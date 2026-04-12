import json
from pathlib import Path
from typing import cast

import pytest

import machineconfig.scripts.python.helpers.helpers_agents.privacy.configs.droid.droid_privacy as droid_privacy_module
from machineconfig.scripts.python.helpers.helpers_agents.privacy.configs.droid.droid_privacy import (
    secure_droid_cli,
)


SECURE_SETTINGS: dict[str, bool] = {
    "cloudSessionSync": False,
    "enableDroidShield": True,
    "telemetry": False,
    "caching": False,
    "analytics": False,
    "data_usage": False,
    "dataUsage": False,
}


def read_json_object(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def test_secure_droid_cli_merges_existing_settings(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(droid_privacy_module.Path, "home", lambda: tmp_path)
    config_file = tmp_path / ".factory" / "settings.json"
    config_file.parent.mkdir(parents=True)
    config_file.write_text(
        json.dumps({"custom": "keep", "telemetry": True}), encoding="utf-8"
    )

    secure_droid_cli()

    written_settings = read_json_object(config_file)
    assert written_settings["custom"] == "keep"
    assert {key: written_settings[key] for key in SECURE_SETTINGS} == SECURE_SETTINGS


def test_secure_droid_cli_replaces_invalid_json(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(droid_privacy_module.Path, "home", lambda: tmp_path)
    config_file = tmp_path / ".factory" / "settings.json"
    config_file.parent.mkdir(parents=True)
    config_file.write_text("{not valid json", encoding="utf-8")

    secure_droid_cli()

    assert read_json_object(config_file) == SECURE_SETTINGS
