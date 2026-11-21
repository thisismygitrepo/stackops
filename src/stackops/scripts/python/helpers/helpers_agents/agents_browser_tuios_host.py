from collections.abc import Sequence
from pathlib import Path
import platform
import shlex
import shutil

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import BROWSER_MULTIPLEXER_SESSION_NAME, BROWSER_TUIOS_WORKSPACE
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_models import BrowserWindowHandle
from stackops.scripts.python.helpers.helpers_sessions._attach_common import quote_powershell
from stackops.scripts.python.helpers.helpers_sessions._tuios_backend import focus_window_attach_script
from stackops.scripts.python.helpers.helpers_sessions._tuios_backend_state import list_session_entries, list_window_entries, run_tuios
from stackops.scripts.python.helpers.helpers_sessions.sessions_tuios_commands import close_window, launch_window


def open_tuios_browser_windows(*, launch_id: str, browser_command: Sequence[str], relay_command: Sequence[str] | None) -> BrowserWindowHandle:
    if shutil.which("tuios") is None:
        raise RuntimeError("tuios is required for browser tuios launches. Pass --runtime detached to use background processes.")
    session_name = BROWSER_MULTIPLEXER_SESSION_NAME
    bootstrap_window_ids: list[str] = []
    if not _session_is_running(session_name=session_name):
        run_tuios(["new", "--detach", "--", session_name])
        bootstrap_window_ids = [window.window_id for window in list_window_entries(session_name)]
    window_ids = [_open_window(window_name=f"{launch_id}-endpoint", command=browser_command)]
    if relay_command is not None:
        window_ids.append(_open_window(window_name=f"{launch_id}-relay", command=relay_command))
    for bootstrap_window_id in bootstrap_window_ids:
        close_window(session_name=session_name, window_id=bootstrap_window_id)
    return BrowserWindowHandle(
        multiplexer="tuios",
        session_name=session_name,
        targets=tuple(window_ids),
        attach_script=focus_window_attach_script(session_name=session_name, window_id=window_ids[0]),
    )


def open_tuios_relay_window(*, handle: BrowserWindowHandle, launch_id: str, relay_command: Sequence[str]) -> BrowserWindowHandle:
    relay_window_id = _open_window(window_name=f"{launch_id}-relay", command=relay_command)
    return BrowserWindowHandle(
        multiplexer="tuios",
        session_name=handle.session_name,
        targets=(*handle.targets, relay_window_id),
        attach_script=handle.attach_script,
    )


def close_tuios_browser_windows(*, handle: BrowserWindowHandle) -> None:
    if not _session_is_running(session_name=handle.session_name):
        return
    existing_window_ids = {window.window_id for window in list_window_entries(handle.session_name)}
    for window_id in handle.targets:
        if window_id in existing_window_ids:
            close_window(session_name=handle.session_name, window_id=window_id)


def _session_is_running(*, session_name: str) -> bool:
    return any(session.name == session_name and not session.saved for session in list_session_entries())


def _open_window(*, window_name: str, command: Sequence[str]) -> str:
    return launch_window(
        session_name=BROWSER_MULTIPLEXER_SESSION_NAME,
        pane={"paneName": window_name, "startDir": str(Path.home()), "command": _window_command_text(command=command)},
        exit_mode="backToShell",
        workspace=BROWSER_TUIOS_WORKSPACE,
    )


def _window_command_text(*, command: Sequence[str]) -> str:
    if platform.system() == "Windows":
        return "& " + " ".join(quote_powershell(part) for part in command)
    return shlex.join(command)
