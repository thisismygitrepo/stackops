from __future__ import annotations

import json
from pathlib import Path

import pytest

from machineconfig.scripts.python.helpers.helpers_agents.privacy.configs.qwen import (
    qwen_privacy,
)


def test_secure_qwen_config_creates_expected_defaults(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class FakePath:
        @staticmethod
        def home() -> Path:
            return tmp_path

    monkeypatch.setattr(qwen_privacy, "Path", FakePath)

    qwen_privacy.secure_qwen_config()

    config_file = tmp_path.joinpath(".qwen", "settings.json")
    content = json.loads(config_file.read_text(encoding="utf-8"))

    assert content["privacy"]["usageStatisticsEnabled"] is False
    assert content["telemetry"] == {
        "enabled": False,
        "logPrompts": False,
        "target": "local",
    }
    assert content["general"]["disableAutoUpdate"] is True
    assert content["general"]["checkpointing"]["enabled"] is False


def test_secure_qwen_config_recovers_from_invalid_json(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class FakePath:
        @staticmethod
        def home() -> Path:
            return tmp_path

    monkeypatch.setattr(qwen_privacy, "Path", FakePath)
    config_dir = tmp_path.joinpath(".qwen")
    config_dir.mkdir(parents=True)
    config_dir.joinpath("settings.json").write_text("{not-json", encoding="utf-8")

    qwen_privacy.secure_qwen_config()

    content = json.loads(config_dir.joinpath("settings.json").read_text(encoding="utf-8"))
    assert content["privacy"]["usageStatisticsEnabled"] is False
    assert content["telemetry"]["enabled"] is False
    assert content["general"]["checkpointing"]["enabled"] is False
