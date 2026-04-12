from pathlib import Path
import subprocess
from typing import cast

import pytest

import machineconfig.jobs.installer.linux_scripts as linux_scripts
import machineconfig.jobs.installer.python_scripts.redis as redis
from machineconfig.utils.path_reference import get_path_reference_path
from machineconfig.utils.schemas.installer.installer_types import InstallerData


def _installer_data() -> InstallerData:
    return cast(InstallerData, {})


def test_linux_script_reference_exists() -> None:
    script_path = get_path_reference_path(module=linux_scripts, path_reference=linux_scripts.REDIS_PATH_REFERENCE)

    assert script_path.is_file()
    assert script_path.suffix == ".sh"


def test_linux_main_executes_repo_script(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    script_path = tmp_path / "redis.sh"
    script_path.write_text("echo install redis", encoding="utf-8")
    recorded_calls: list[tuple[str, bool, bool, bool]] = []

    def fake_get_path_reference_path(*, module: object, path_reference: str) -> Path:
        _ = module, path_reference
        return script_path

    def fake_run(program: str, shell: bool, text: bool, check: bool) -> subprocess.CompletedProcess[str]:
        recorded_calls.append((program, shell, text, check))
        return subprocess.CompletedProcess(args=[program], returncode=0, stdout="")

    monkeypatch.setattr(redis.platform, "system", lambda: "Linux")
    monkeypatch.setattr(redis, "get_path_reference_path", fake_get_path_reference_path)
    monkeypatch.setattr(redis.subprocess, "run", fake_run)

    redis.main(installer_data=_installer_data(), version=None, update=False)

    assert recorded_calls == [("echo install redis", True, True, True)]


def test_darwin_main_uses_homebrew(monkeypatch: pytest.MonkeyPatch) -> None:
    recorded_calls: list[tuple[str, bool, bool, bool]] = []

    def fake_run(program: str, shell: bool, text: bool, check: bool) -> subprocess.CompletedProcess[str]:
        recorded_calls.append((program, shell, text, check))
        return subprocess.CompletedProcess(args=[program], returncode=0, stdout="")

    monkeypatch.setattr(redis.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(redis.subprocess, "run", fake_run)

    redis.main(installer_data=_installer_data(), version=None, update=False)

    assert recorded_calls == [("brew install redis", True, True, True)]


def test_windows_main_is_not_supported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(redis.platform, "system", lambda: "Windows")

    with pytest.raises(NotImplementedError, match="Redis installation not supported on Windows"):
        redis.main(installer_data=_installer_data(), version=None, update=False)
