import json
from pathlib import Path


def secure_droid_cli() -> None:
    config_dir = Path.home() / ".factory"
    config_file = config_dir / "settings.json"
    config_dir.mkdir(parents=True, exist_ok=True)

    settings = {}
    if config_file.exists():
        try:
            settings = json.loads(config_file.read_text(encoding="utf-8"))
        except Exception:
            pass
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
