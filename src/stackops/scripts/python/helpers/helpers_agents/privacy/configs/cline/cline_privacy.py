import json
import os
from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.privacy.configs.common.json_settings import read_privacy_settings


def secure_cline_config() -> None:
    home = Path.home()
    vscode_storage = home / ".config" / "Code" / "User" / "globalStorage" / "saoudrizwan.cline"
    config_paths = [
        home / ".cline" / "settings.json",
        home / ".cline" / "config.json",
        home / ".config" / "cline" / "settings.json",
        vscode_storage / "settings.json",
        vscode_storage / "settings" / "settings.json",
    ]
    privacy_settings = {
        "telemetry": False,
        "telemetry.enabled": False,
        "disableTelemetry": True,
        "analytics": False,
        "allowAnalytics": False,
        "allowDataUsage": False,
        "dataCollection": False,
        "crashReporting": False,
        "cache": False,
        "enableCaching": False,
        "disableCaching": True,
        "history": False,
        "recordHistory": False,
    }
    for path in config_paths:
        config_data = read_privacy_settings(path)
        if config_data is None:
            continue
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            config_data.update(privacy_settings)
            path.write_text(json.dumps(config_data, indent=4), encoding="utf-8")
            os.chmod(path, 0o600)
        except Exception:
            pass
