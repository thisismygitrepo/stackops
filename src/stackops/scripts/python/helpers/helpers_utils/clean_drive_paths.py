import os
import tempfile
from pathlib import Path
from typing import get_args

from stackops.scripts.python.helpers.helpers_utils.clean_drive_constants import MIN_REMOVABLE_PATH_PARTS
from stackops.scripts.python.helpers.helpers_utils.clean_drive_models import Anchor, PathGlob


def anchor_directory(anchor: Anchor) -> Path | None:
    home = Path.home()
    xdg_cache = Path(os.environ.get("XDG_CACHE_HOME") or home / ".cache")
    match anchor:
        case "home":
            return home
        case "xdg_cache":
            return xdg_cache
        case "xdg_data":
            return Path(os.environ.get("XDG_DATA_HOME") or home / ".local" / "share")
        case "xdg_config":
            return Path(os.environ.get("XDG_CONFIG_HOME") or home / ".config")
        case "mac_caches":
            return home / "Library" / "Caches"
        case "local_app_data":
            local_app_data = os.environ.get("LOCALAPPDATA")
            return None if local_app_data is None or local_app_data == "" else Path(local_app_data)
        case "temp":
            return Path(tempfile.gettempdir())
        case "system_root":
            system_root = os.environ.get("SystemRoot")
            return None if system_root is None or system_root == "" else Path(system_root)
        case "cargo_home":
            return Path(os.environ.get("CARGO_HOME") or home / ".cargo")
        case "gradle_home":
            return Path(os.environ.get("GRADLE_USER_HOME") or home / ".gradle")
        case "hf_home":
            return Path(os.environ.get("HF_HOME") or xdg_cache / "huggingface")
        case "filesystem_root":
            return Path(home.anchor)


def expand_globs(globs: tuple[PathGlob, ...]) -> list[Path]:
    matches: list[Path] = []
    for path_glob in globs:
        base = anchor_directory(path_glob.anchor)
        if base is not None and base.is_dir():
            matches.extend(sorted(base.glob(path_glob.pattern)))
    return list(dict.fromkeys(matches))


def removal_block_reason(path: Path) -> str | None:
    candidate = path.parent.resolve() / path.name
    if len(candidate.parts) < MIN_REMOVABLE_PATH_PARTS:
        return f"""refusing to remove top-level path {candidate}"""
    if Path.home().resolve().is_relative_to(candidate):
        return f"""refusing to remove {candidate}: it contains the home directory"""
    anchor_roots = {directory.resolve() for anchor in get_args(Anchor.__value__) if (directory := anchor_directory(anchor)) is not None}
    if candidate in anchor_roots:
        return f"""refusing to remove {candidate}: it is a base directory"""
    return None
