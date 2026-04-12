from __future__ import annotations

import json
from pathlib import Path
from stat import S_IMODE
from typing import cast

import pytest

from machineconfig.scripts.python.helpers.helpers_agents.privacy.configs.auggie import auggie_privacy as module


def _read_json_object(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def test_secure_auggie_config_overwrites_privacy_sensitive_settings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    settings_file = tmp_path / ".augment" / "settings.json"
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    settings_file.write_text(
        json.dumps({"keep": "value", "featureFlagOverrides": {"cache": True}}),
        encoding="utf-8",
    )

    module.secure_auggie_config()
    settings = _read_json_object(settings_file)

    assert settings["keep"] == "value"
    assert settings["indexingAllowDirs"] == []
    assert settings["indexingDenyDirs"] == ["/"]
    assert settings["autoUpdate"] is False
    assert settings["toolPermissions"] == []
    assert settings["telemetry"] is False
    assert settings["dataUsage"] == "deny"
    assert settings["cache"] == "none"
    feature_flags = settings["featureFlagOverrides"]
    assert isinstance(feature_flags, dict)
    assert feature_flags["telemetry"] is False
    assert feature_flags["cache"] == "none"
    assert S_IMODE(settings_file.stat().st_mode) == 0o600


def test_secure_auggie_config_recovers_from_invalid_existing_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    settings_file = tmp_path / ".augment" / "settings.json"
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    settings_file.write_text('{"broken": }', encoding="utf-8")

    module.secure_auggie_config()
    settings = _read_json_object(settings_file)

    assert settings["indexingAllowDirs"] == []
    assert settings["toolPermissions"] == []
    assert settings["telemetryEnabled"] is False
