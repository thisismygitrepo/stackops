from collections.abc import Sequence
from pathlib import Path
import shlex

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import BROWSER_MULTIPLEXER_SESSION_NAME
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_models import BrowserWindowHandle
from stackops.scripts.python.helpers.helpers_sessions._zellij_backend import attach_session_script
from stackops.scripts.python.helpers.helpers_sessions._zellij_backend_models import PaneEntry
from stackops.scripts.python.helpers.helpers_sessions._zellij_backend_state import list_session_names, list_tab_entries, require_zellij, run_zellij
from stackops.scripts.python.helpers.helpers_sessions.sessions_zellij_layout import launch_session, launch_tab
from stackops.utils.schemas.layouts.layout_types import PaneConfig, TabConfig


def open_zellij_browser_windows(*, launch_id: str, browser_command: Sequence[str], relay_command: Sequence[str] | None) -> BrowserWindowHandle:
    require_zellij()
    panes = [_pane(pane_name=f"{launch_id}-endpoint", command=browser_command)]
    if relay_command is not None:
        panes.append(_pane(pane_name=f"{launch_id}-relay", command=relay_command))
    launched_panes = _launch_tab(tab={"tabName": launch_id, "panes": panes})
    return BrowserWindowHandle(
        multiplexer="zellij",
        session_name=BROWSER_MULTIPLEXER_SESSION_NAME,
        targets=(str(launched_panes[0].tab_id),),
        attach_script=attach_session_script(BROWSER_MULTIPLEXER_SESSION_NAME, None, launched_panes[0]),
    )


def open_zellij_relay_window(*, handle: BrowserWindowHandle, launch_id: str, relay_command: Sequence[str]) -> BrowserWindowHandle:
    require_zellij()
    launched_panes = _launch_tab(tab={"tabName": f"{launch_id}-relay", "panes": [_pane(pane_name=f"{launch_id}-relay", command=relay_command)]})
    return BrowserWindowHandle(
        multiplexer="zellij",
        session_name=handle.session_name,
        targets=(*handle.targets, str(launched_panes[0].tab_id)),
        attach_script=handle.attach_script,
    )


def close_zellij_browser_windows(*, handle: BrowserWindowHandle) -> None:
    require_zellij()
    if handle.session_name not in list_session_names():
        return
    existing_tab_ids = {str(tab.tab_id) for tab in list_tab_entries(handle.session_name)}
    for tab_id in handle.targets:
        if tab_id in existing_tab_ids:
            run_zellij(["--session", handle.session_name, "action", "close-tab", "--tab-id", tab_id])


def _pane(*, pane_name: str, command: Sequence[str]) -> PaneConfig:
    return {"paneName": pane_name, "startDir": str(Path.home()), "command": shlex.join(command)}


def _launch_tab(*, tab: TabConfig) -> list[PaneEntry]:
    if BROWSER_MULTIPLEXER_SESSION_NAME in list_session_names():
        launched_panes = launch_tab(session_name=BROWSER_MULTIPLEXER_SESSION_NAME, tab=tab, exit_mode="backToShell")
    else:
        launched_panes = launch_session(
            session_name=BROWSER_MULTIPLEXER_SESSION_NAME,
            layout={"layoutName": BROWSER_MULTIPLEXER_SESSION_NAME, "layoutTabs": [tab]},
            exit_mode="backToShell",
        )
    if not launched_panes:
        raise RuntimeError(f"""Zellij did not report any pane for browser tab '{tab['tabName']}'.""")
    return launched_panes
