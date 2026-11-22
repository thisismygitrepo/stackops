import json
import os
import pathlib

from stackops.scripts.python.helpers.helpers_agents.privacy.configs.common.json_settings import read_privacy_settings


def secure_chatgpt_cli() -> None:
    config_paths = [
        "~/.config/chatgpt.json",
        "~/.config/chatgpt-cli/config.json",
        "~/.chatgpt",
        "~/.chatgpt.json",
    ]
    privacy_settings = {
        "telemetry": False,
        "analytics": False,
        "track": False,
        "cache": False,
        "save_history": False,
        "history": False,
        "data_usage": False,
        "send_usage_stats": False,
        "store": False,
        "share_data": False,
        "record": False,
    }
    for path_str in config_paths:
        path = pathlib.Path(path_str).expanduser()
        config_data = read_privacy_settings(path)
        if config_data is None:
            continue
        if not path.parent.exists():
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
            except Exception:
                continue
        config_data.update(privacy_settings)
        try:
            path.write_text(json.dumps(config_data, indent=4), encoding="utf-8")
            os.chmod(path, 0o600)
        except Exception:
            pass
