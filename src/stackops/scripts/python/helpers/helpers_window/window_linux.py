import os
import shutil
import subprocess
from functools import partial

from stackops.scripts.python.helpers.helpers_window.window_models import WindowAction, WindowEntry


def collect_windows() -> list[WindowEntry]:
    if os.environ.get("WAYLAND_DISPLAY") or os.environ.get("XDG_SESSION_TYPE", "").casefold() == "wayland":
        raise RuntimeError("Window management requires an X11 desktop on Linux; native Wayland sessions are unsupported.")
    if not os.environ.get("DISPLAY"):
        raise RuntimeError("Window management requires a graphical desktop; DISPLAY is not set.")

    entries: list[WindowEntry] = []
    for line in _run_command(["wmctrl", "-lxp", "-u"]).splitlines():
        fields = line.split(maxsplit=5)
        if len(fields) < 5:
            raise RuntimeError(f"""wmctrl returned an invalid window entry: {line}""")
        window_id, _desktop_id, _process_id, app, _machine = fields[:5]
        state = _run_command(["xprop", "-id", window_id, "WM_STATE"])
        state_line = next((item.strip() for item in state.splitlines() if item.strip().startswith("window state: ")), None)
        if state_line is None:
            raise RuntimeError(f"""Could not read the minimized state of window {window_id}.""")
        entries.append(
            WindowEntry(
                app=app,
                title=fields[5] if len(fields) == 6 else "",
                minimized=state_line == "window state: Iconic",
                apply_action=partial(_apply_action, window_id),
            )
        )
    return entries


def _run_command(arguments: list[str]) -> str:
    executable = arguments[0]
    if shutil.which(executable) is None:
        raise RuntimeError(f"""Window management requires the {executable} command in PATH.""")
    try:
        process = subprocess.run(
            arguments,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env={**os.environ, "LC_ALL": "C"},
            check=False,
            timeout=10,
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(f"""{executable} did not finish the window operation within 10 seconds.""") from error
    except OSError as error:
        raise RuntimeError(f"""Could not run {executable}: {error}""") from error
    if process.returncode != 0:
        reason = process.stderr.strip() or process.stdout.strip() or f"""exit status {process.returncode}"""
        raise RuntimeError(f"""{executable} failed: {reason}""")
    return process.stdout


def _apply_action(window_id: str, action: WindowAction) -> None:
    match action:
        case "minimize":
            _run_command(["xdotool", "windowminimize", "--sync", window_id])
        case "maximize":
            _run_command(["wmctrl", "-i", "-a", window_id])
            _run_command(["wmctrl", "-i", "-r", window_id, "-b", "add,maximized_vert,maximized_horz"])
        case "unminimize" | "focus":
            _run_command(["wmctrl", "-i", "-a", window_id])
        case "close":
            _run_command(["wmctrl", "-i", "-c", window_id])
