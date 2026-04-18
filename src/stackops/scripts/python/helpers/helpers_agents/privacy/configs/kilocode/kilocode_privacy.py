import json
import os
from pathlib import Path


def secure_kilocode_config() -> None:
    config_dir = Path.home() / ".config" / "kilocode"
    config_dir.mkdir(parents=True, exist_ok=True)
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
    current_config = {}
    if config_file.exists():
        try:
            current_config = json.loads(config_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    current_config.update(secure_settings)
    config_file.write_text(json.dumps(current_config, indent=4), encoding="utf-8")
    try:
        os.chmod(config_file, 0o600)
    except Exception:
        pass
