import json
import os
import shutil
import subprocess
from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.privacy.configs.common.json_settings import read_privacy_settings


def secure_q_cli() -> None:
    privacy_settings = {
        "telemetry.enabled": False,
        "telemetry.disabled": True,
        "chat.shareData": False,
        "completion.shareData": False,
        "caching.enabled": False,
        "cache.enabled": False,
        "aws.telemetry": False,
        "diagnostics.crashReporter": False,
    }
    home = Path.home()
    config_paths = [
        home / ".config" / "amazon-q" / "settings.json",
        home / ".amazon-q" / "settings.json",
        home / ".aws" / "amazon-q" / "settings.json",
        home / ".config" / "kiro" / "settings.json",
        home / ".kiro" / "settings.json",
    ]
    read_failed = False
    for config_file in config_paths:
        current_settings = read_privacy_settings(config_file)
        if current_settings is None:
            read_failed = True
            continue
        try:
            config_file.parent.mkdir(parents=True, exist_ok=True)
            current_settings.update(privacy_settings)
            config_file.write_text(json.dumps(current_settings, indent=2), encoding="utf-8")
            if os.name != "nt":
                config_file.chmod(0o600)
        except Exception:
            pass
    if read_failed:
        # Either CLI could write to a settings file we skipped.
        return
    for exe in ["q", "kiro"]:
        if shutil.which(exe) is not None:
            for key, value in privacy_settings.items():
                val_str = "true" if value else "false"
                try:
                    subprocess.run(
                        [exe, "settings", key, val_str],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=False,
                    )
                except Exception:
                    pass
