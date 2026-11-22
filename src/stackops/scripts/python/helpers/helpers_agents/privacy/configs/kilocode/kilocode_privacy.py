import json
import os
from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.privacy.configs.common.json_settings import read_privacy_settings


def secure_kilocode_config() -> None:
    config_dir = Path.home() / ".config" / "kilocode"
    config_file = config_dir / "config.json"
    secure_settings = {
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
    current_config = read_privacy_settings(config_file)
    if current_config is None:
        return
    config_dir.mkdir(parents=True, exist_ok=True)
    current_config.update(secure_settings)
    config_file.write_text(json.dumps(current_config, indent=4), encoding="utf-8")
    try:
        os.chmod(config_file, 0o600)
    except Exception:
        pass
