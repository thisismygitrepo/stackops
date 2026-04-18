import os
import re
from pathlib import Path


def secure_mods_config() -> None:
    config_dir = Path(os.getenv("XDG_CONFIG_HOME", str(Path.home() / ".config")))
    mods_dir = config_dir / "mods"
    config_file = mods_dir / "mods.yml"
    mods_dir.mkdir(parents=True, exist_ok=True)

    content = ""
    if config_file.exists():
        content = config_file.read_text(encoding="utf-8")

    privacy_settings = {
        "no-cache": "true",
        "cache-path": '"/dev/null"',
        "telemetry": "false",
    }

    for key, value in privacy_settings.items():
        pattern = rf"^[#\s]*{key}\s*:.*$"
        if re.search(pattern, content, flags=re.MULTILINE):
            content = re.sub(pattern, f"{key}: {value}", content, flags=re.MULTILINE)
        else:
            if not content.endswith("\n") and content != "":
                content += "\n"
            content += f"{key}: {value}\n"

    config_file.write_text(content.strip() + "\n", encoding="utf-8")
    try:
        os.chmod(config_file, 0o600)
    except Exception:
        pass
