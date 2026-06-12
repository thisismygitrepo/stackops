import os
import platform
import shutil
from pathlib import Path

from stackops.utils.source_of_truth import LINUX_INSTALL_PATH, WINDOWS_INSTALL_PATH


def check_tool_exists(tool_name: str) -> bool:
    if shutil.which(tool_name) is not None:
        return True

    tool_name_without_exe = tool_name.removesuffix(".exe")
    if platform.system() == "Windows":
        candidates = (
            Path(WINDOWS_INSTALL_PATH) / f"{tool_name_without_exe}.exe",
            Path.home() / "AppData" / "Roaming" / "npm" / tool_name_without_exe,
            Path.home() / "AppData" / "Roaming" / "npm" / f"{tool_name_without_exe}.cmd",
        )
        return any(path.exists() for path in candidates)

    if platform.system() in ("Linux", "Darwin"):
        return (Path(LINUX_INSTALL_PATH) / tool_name).exists()

    return False


def is_executable_in_path(name: str) -> bool:
    path_value = os.environ.get("PATH")
    if path_value is None:
        return False
    for path_dir in path_value.split(os.pathsep):
        candidate = Path(path_dir) / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return True
    return False
