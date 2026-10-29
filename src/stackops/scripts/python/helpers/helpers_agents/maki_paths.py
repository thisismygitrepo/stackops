import os
from pathlib import Path
from platform import system


def resolve_maki_config_directory(*, home_dir: Path) -> Path:
    if system() == "Windows":
        configured = os.environ.get("APPDATA", "").strip()
        directory = Path(configured).expanduser() if configured else home_dir / "AppData/Roaming"
    else:
        configured = os.environ.get("XDG_CONFIG_HOME", "").strip()
        directory = Path(configured).expanduser() if configured else home_dir / ".config"
    return directory / "maki"
