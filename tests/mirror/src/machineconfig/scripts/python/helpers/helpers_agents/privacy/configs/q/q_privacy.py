import json
import subprocess
from pathlib import Path
from typing import cast

import pytest

import machineconfig.scripts.python.helpers.helpers_agents.privacy.configs.q.q_privacy as q_privacy_module
from machineconfig.scripts.python.helpers.helpers_agents.privacy.configs.q.q_privacy import secure_q_cli


SECURE_SETTINGS: dict[str, bool] = {
    "telemetry.enabled": False,
    "telemetry.disabled": True,
    "chat.shareData": False,
    "completion.shareData": False,
    "caching.enabled": False,
    "cache.enabled": False,
    "aws.telemetry": False,
    "diagnostics.crashReporter": False,
}
CONFIG_RELATIVE_PATHS: tuple[Path, ...] = (
    Path(".config/amazon-q/settings.json"),
    Path(".amazon-q/settings.json"),
    Path(".aws/amazon-q/settings.json"),
    Path(".config/kiro/settings.json"),
    Path(".kiro/settings.json"),
)


def read_json_object(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def fake_which(_executable: str) -> str:
    return "/usr/bin/fake"


def test_secure_q_cli_updates_all_known_config_files_and_syncs_cli(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    recorded_calls: list[tuple[str, ...]] = []

    def fake_run(args: list[str], stdout: object, stderr: object, check: bool) -> subprocess.CompletedProcess[list[str]]:
        recorded_calls.append(tuple(args))
        return subprocess.CompletedProcess(args=args, returncode=0)

    monkeypatch.setattr(q_privacy_module.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(q_privacy_module.shutil, "which", fake_which)
    monkeypatch.setattr(q_privacy_module.subprocess, "run", fake_run)

    merged_file = tmp_path / CONFIG_RELATIVE_PATHS[0]
    merged_file.parent.mkdir(parents=True)
    merged_file.write_text(json.dumps({"custom": "keep", "telemetry.enabled": True}), encoding="utf-8")
    invalid_file = tmp_path / CONFIG_RELATIVE_PATHS[1]
    invalid_file.parent.mkdir(parents=True)
    invalid_file.write_text("{not valid json", encoding="utf-8")

    secure_q_cli()

    assert read_json_object(merged_file)["custom"] == "keep"
    assert read_json_object(invalid_file) == SECURE_SETTINGS
    for relative_path in CONFIG_RELATIVE_PATHS:
        config_file = tmp_path / relative_path
        written_settings = read_json_object(config_file)
        assert {key: written_settings[key] for key in SECURE_SETTINGS} == SECURE_SETTINGS
        assert config_file.stat().st_mode & 0o777 == 0o600
    assert len(recorded_calls) == 2 * len(SECURE_SETTINGS)
    assert ("q", "settings", "telemetry.enabled", "false") in recorded_calls
    assert ("kiro", "settings", "telemetry.disabled", "true") in recorded_calls


def test_secure_q_cli_ignores_cli_sync_failures(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    recorded_calls: list[tuple[str, ...]] = []

    def fake_run(args: list[str], stdout: object, stderr: object, check: bool) -> subprocess.CompletedProcess[list[str]]:
        recorded_calls.append(tuple(args))
        raise OSError("run failed")

    monkeypatch.setattr(q_privacy_module.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(q_privacy_module.shutil, "which", lambda executable: "/usr/bin/q" if executable == "q" else None)
    monkeypatch.setattr(q_privacy_module.subprocess, "run", fake_run)

    secure_q_cli()

    assert len(recorded_calls) == len(SECURE_SETTINGS)
    for relative_path in CONFIG_RELATIVE_PATHS:
        assert (tmp_path / relative_path).exists()
