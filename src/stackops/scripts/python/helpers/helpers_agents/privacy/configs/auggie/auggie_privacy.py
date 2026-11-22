import json
from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.privacy.configs.common.json_settings import read_privacy_settings


def secure_auggie_config() -> None:
    config_dir = Path.home() / ".augment"
    settings_file = config_dir / "settings.json"
    settings = read_privacy_settings(settings_file)
    if settings is None:
        return
    config_dir.mkdir(parents=True, exist_ok=True)
    settings["indexingAllowDirs"] = []
    settings["indexingDenyDirs"] = ["/"]
    settings["autoUpdate"] = False
    settings["toolPermissions"] = []
    privacy_flags = {
        "telemetry": False,
        "telemetryEnabled": False,
        "optInTelemetry": False,
        "analytics": False,
        "shareData": False,
        "dataUsage": "deny",
        "cache": "none",
        "caching": False,
    }
    settings.update(privacy_flags)
    feature_flags = settings.get("featureFlagOverrides", {})
    if isinstance(feature_flags, dict):
        feature_flags.update(privacy_flags)
        settings["featureFlagOverrides"] = feature_flags
    settings_file.write_text(json.dumps(settings, indent=2))
    try:
        settings_file.chmod(0o600)
    except Exception:
        pass
