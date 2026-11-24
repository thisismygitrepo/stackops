import os
import shutil
import subprocess
import sys
from pathlib import Path

import psutil

from stackops.scripts.python.helpers.helpers_webui.machine_windows_constants import MINIMIZE_NEEDS_XDOTOOL
from stackops.scripts.python.helpers.helpers_webui.machine_windows_models import WindowsProblem, WindowsUnavailable, WindowsView, WindowView
from stackops.scripts.python.helpers.helpers_window.window_models import WindowEntry


# The same choice of helper the `window` command makes for the system it runs on.
def collect_open_windows() -> list[WindowEntry]:
    if sys.platform == "darwin":
        from stackops.scripts.python.helpers.helpers_window.window_macos import collect_windows
    elif sys.platform == "linux":
        from stackops.scripts.python.helpers.helpers_window.window_linux import collect_windows
    elif sys.platform == "win32":
        from stackops.scripts.python.helpers.helpers_window.window_windows import collect_windows
    else:
        raise RuntimeError(f"""Window management is not supported on {sys.platform}.""")
    return collect_windows()


# On Windows the CLI names a window's app by its process number; the page groups by the program's name instead.
def _program_name(entry: WindowEntry) -> str:
    try:
        return Path(psutil.Process(int(entry.id.split(":")[1])).name()).stem
    except (psutil.Error, ValueError):
        return entry.app


# What the Windows page shows on arrival. The three ways a machine can be unable to list its windows at all are told apart before the helper
# is asked, by the same tests the helper makes, because each gets a page of its own; anything else the helper refuses comes back in its words.
def read_windows() -> WindowsView | WindowsUnavailable | WindowsProblem:
    if sys.platform not in ("darwin", "linux", "win32"):
        return {"available": False, "reason": "unsupported_system", "launcher": ""}
    if sys.platform == "linux" and (os.environ.get("WAYLAND_DISPLAY", "") != "" or os.environ.get("XDG_SESSION_TYPE", "").casefold() == "wayland"):
        return {"available": False, "reason": "wayland", "launcher": ""}
    if sys.platform == "darwin":
        from stackops.scripts.python.helpers.helpers_webui.machine_windows_macos import launcher_app
        from stackops.scripts.python.helpers.helpers_window import window_macos_api as api

        if not api.AX.AXIsProcessTrusted():
            return {"available": False, "reason": "permission", "launcher": launcher_app()}
    blocked = {"minimize": MINIMIZE_NEEDS_XDOTOOL} if sys.platform == "linux" and shutil.which("xdotool") is None else {}
    try:
        entries = collect_open_windows()
        if sys.platform == "darwin":
            from stackops.scripts.python.helpers.helpers_webui.machine_windows_macos import describe_macos_windows, read_macos_screens

            return {"available": True, "windows": describe_macos_windows(entries), "screens": read_macos_screens(), "blocked": blocked}
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as error:
        return WindowsProblem(status=502, message=str(error))
    windows: list[WindowView] = [
        {
            "id": entry.id, "app": _program_name(entry) if sys.platform == "win32" else entry.app, "title": entry.title,
            "minimized": entry.minimized, "hidden": False, "full_screen": False, "frame": None,
        }
        for entry in entries
    ]
    return {"available": True, "windows": windows, "screens": [], "blocked": blocked}
