import json
from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.privacy.configs.common.json_settings import read_privacy_settings


def secure_droid_cli() -> None:
    config_dir = Path.home() / ".factory"
    config_file = config_dir / "settings.json"
    settings = read_privacy_settings(config_file)
    if settings is None:
        return
    config_dir.mkdir(parents=True, exist_ok=True)
    settings.update(
        {
            "cloudSessionSync": False,
            "enableDroidShield": True,
            "telemetry": False,
            "caching": False,
            "analytics": False,
            "data_usage": False,
            "dataUsage": False,
        }
    )
    config_file.write_text(json.dumps(settings, indent=2), encoding="utf-8")
