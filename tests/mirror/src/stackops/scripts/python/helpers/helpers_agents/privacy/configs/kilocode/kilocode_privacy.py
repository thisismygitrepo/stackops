import json
from pathlib import Path
from typing import cast

import pytest

import stackops.scripts.python.helpers.helpers_agents.privacy.configs.kilocode.kilocode_privacy as kilocode_privacy_module
from stackops.scripts.python.helpers.helpers_agents.privacy.configs.kilocode.kilocode_privacy import secure_kilocode_config


SECURE_SETTINGS: dict[str, bool | str] = {
    "telemetry": False,
    "analytics_opt_in": False,
    "caching": False,
    "cache_enabled": False,
    "data_usage": "reject",
    "crash_reporting": False,
    "send_usage_metrics": False,
    "allow_tracking": False,
    "telemetry_enabled": False,
    "offline_mode": True,
}


def read_json_object(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def raise_os_error(_path: object, _mode: int) -> None:
    raise OSError("chmod failed")


def test_secure_kilocode_config_merges_existing_settings_and_sets_permissions(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(kilocode_privacy_module.Path, "home", lambda: tmp_path)
    config_file = tmp_path / ".config" / "kilocode" / "config.json"
    config_file.parent.mkdir(parents=True)
    config_file.write_text(json.dumps({"custom": 7, "telemetry": True}), encoding="utf-8")

    secure_kilocode_config()

    written_config = read_json_object(config_file)
    assert written_config["custom"] == 7
    assert {key: written_config[key] for key in SECURE_SETTINGS} == SECURE_SETTINGS
    assert config_file.stat().st_mode & 0o777 == 0o600


def test_secure_kilocode_config_ignores_invalid_json_and_chmod_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(kilocode_privacy_module.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(kilocode_privacy_module.os, "chmod", raise_os_error)
    config_file = tmp_path / ".config" / "kilocode" / "config.json"
    config_file.parent.mkdir(parents=True)
    config_file.write_text("{not valid json", encoding="utf-8")

    secure_kilocode_config()

    assert read_json_object(config_file) == SECURE_SETTINGS
