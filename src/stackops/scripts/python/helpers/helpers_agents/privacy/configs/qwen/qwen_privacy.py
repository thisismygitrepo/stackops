import json
from pathlib import Path
from typing import cast

from stackops.scripts.python.helpers.helpers_agents.privacy.configs.common.json_settings import read_privacy_settings


def secure_qwen_config() -> None:
    config_dir = Path.home() / ".qwen"
    config_file = config_dir / "settings.json"
    config = read_privacy_settings(config_file)
    if config is None:
        return
    privacy = cast(dict[str, object], config.setdefault("privacy", {}))
    privacy["usageStatisticsEnabled"] = False
    telemetry = cast(dict[str, object], config.setdefault("telemetry", {}))
    telemetry.update(enabled=False, logPrompts=False, target="local")
    general = cast(dict[str, object], config.setdefault("general", {}))
    general["disableAutoUpdate"] = True
    checkpointing = cast(dict[str, object], general.setdefault("checkpointing", {}))
    checkpointing["enabled"] = False

    config_dir.mkdir(parents=True, exist_ok=True)
    config_file.write_text(json.dumps(config, indent=2), encoding="utf-8")
