import os
import platform
import shutil
import sys
from pathlib import Path

from stackops.utils.source_of_truth import LINUX_INSTALL_PATH, WINDOWS_INSTALL_PATH


def check_tool_exists(tool_name: str) -> bool:
    if shutil.which(tool_name) is not None:
        return True

    if sys.platform == "win32":
        # installers record PATH changes in the registry, while this process keeps the PATH it was started with
        import winreg

        registry_entries: list[str] = []
        for registry_root, environment_key in (
            (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
            (winreg.HKEY_CURRENT_USER, "Environment"),
        ):
            with winreg.OpenKey(registry_root, environment_key) as opened_key:
                try:
                    registry_value, _value_kind = winreg.QueryValueEx(opened_key, "Path")
                except FileNotFoundError:
                    continue
            registry_entries.extend(entry for entry in winreg.ExpandEnvironmentStrings(str(registry_value)).split(os.pathsep) if entry != "")
        process_entries = os.environ["PATH"].split(os.pathsep)
        known_entries = {entry.rstrip("\\").lower() for entry in process_entries}
        added_entries = [entry for entry in registry_entries if entry.rstrip("\\").lower() not in known_entries]
        if len(added_entries) > 0:
            os.environ["PATH"] = os.pathsep.join([*process_entries, *added_entries])
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
