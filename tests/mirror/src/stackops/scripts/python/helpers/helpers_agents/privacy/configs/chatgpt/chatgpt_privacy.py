from __future__ import annotations

import json
from pathlib import Path
from stat import S_IMODE
from typing import Final, cast

import pytest

from stackops.scripts.python.helpers.helpers_agents.privacy.configs.chatgpt import chatgpt_privacy as module


CONFIG_RELATIVE_PATHS: Final[tuple[Path, ...]] = (
    Path(".config/chatgpt.json"),
    Path(".config/chatgpt-cli/config.json"),
    Path(".chatgpt"),
    Path(".chatgpt.json"),
)
PRIVACY_KEYS: Final[tuple[str, ...]] = (
    "telemetry",
    "analytics",
    "track",
    "cache",
    "save_history",
    "history",
    "data_usage",
    "send_usage_stats",
    "store",
    "share_data",
    "record",
)


def _read_json_object(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def test_secure_chatgpt_cli_writes_privacy_settings_to_all_known_config_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    seeded_path = tmp_path / ".config" / "chatgpt.json"
    seeded_path.parent.mkdir(parents=True, exist_ok=True)
    seeded_path.write_text('{"broken": }', encoding="utf-8")

    module.secure_chatgpt_cli()

    for relative_path in CONFIG_RELATIVE_PATHS:
        config_path = tmp_path / relative_path
        assert config_path.is_file()
        config_data = _read_json_object(config_path)
        for key in PRIVACY_KEYS:
            assert config_data[key] is False
        assert S_IMODE(config_path.stat().st_mode) == 0o600
