import json
from pathlib import Path


def secure_qwen_config() -> None:
    config_dir = Path.home() / ".qwen"
    config_file = config_dir / "settings.json"
    config_dir.mkdir(parents=True, exist_ok=True)

    config = {}
    if config_file.exists():
        try:
            config = json.loads(config_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    config.setdefault("privacy", {})["usageStatisticsEnabled"] = False
    config.setdefault("telemetry", {})["enabled"] = False
    config["telemetry"]["logPrompts"] = False
    config["telemetry"]["target"] = "local"
    config.setdefault("general", {})["disableAutoUpdate"] = True
    config["general"].setdefault("checkpointing", {})["enabled"] = False

    config_file.write_text(json.dumps(config, indent=2), encoding="utf-8")
