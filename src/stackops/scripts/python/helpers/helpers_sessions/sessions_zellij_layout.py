import math
from pathlib import Path
from tempfile import TemporaryDirectory
import time
from uuid import uuid4

from stackops.cluster.sessions_managers.session_exit_mode import SessionExitMode
from stackops.scripts.python.helpers.helpers_sessions._zellij_backend_models import PaneEntry, TabEntry
from stackops.scripts.python.helpers.helpers_sessions._zellij_backend_state import (
    list_pane_entries,
    list_session_names,
    list_tab_entries,
    run_zellij,
)
from stackops.scripts.python.helpers.helpers_sessions.sessions_zellij_commands import pane_command_parts
from stackops.scripts.python.helpers.helpers_sessions.sessions_zellij_constants import STARTUP_POLL_SECONDS, STARTUP_TIMEOUT_SECONDS
from stackops.utils.schemas.layouts.layout_constants import DEFAULT_TAB_ARRANGEMENT
from stackops.utils.schemas.layouts.layout_types import LayoutConfig, PaneConfig, TabConfig, resolve_start_dir


def _kdl_string(value: str) -> str:
    escapes = {"\\": "\\\\", '"': '\\"', "\n": "\\n", "\r": "\\r", "\t": "\\t"}
    escaped = "".join(
        escapes[character] if character in escapes else
        f"""\\u{{{ord(character):x}}}""" if ord(character) < 32 else character
        for character in value
    )
    return f'''"{escaped}"'''


def _pane_kdl(pane: PaneConfig, exit_mode: SessionExitMode) -> str:
    start_dir = resolve_start_dir(pane["startDir"])
    command, *arguments = pane_command_parts(command=pane["command"], start_dir=start_dir, exit_mode=exit_mode)
    args = " ".join(_kdl_string(argument) for argument in arguments)
    close_on_exit = "false" if exit_mode == "terminate" else "true"
    return f"""pane name={_kdl_string(pane['paneName'])} cwd={_kdl_string(start_dir)} command={_kdl_string(command)} close_on_exit={close_on_exit} {{
    args {args}
}}"""


def layout_kdl(layout: LayoutConfig, exit_mode: SessionExitMode) -> str:
    tabs: list[str] = []
    if not layout["layoutTabs"]:
        raise ValueError(f"""Zellij cannot launch layout '{layout['layoutName']}' because it has no tabs.""")
    for tab in layout["layoutTabs"]:
        if not tab["panes"]:
            raise ValueError(f"""Zellij cannot launch tab '{tab['tabName']}' because it has no panes.""")
        panes = [_pane_kdl(pane=pane, exit_mode=exit_mode) for pane in tab["panes"]]
        arrangement = tab.get("arrangement", DEFAULT_TAB_ARRANGEMENT)
        direction = "vertical" if arrangement == "columns" else "horizontal"
        if arrangement == "grid":
            columns = math.ceil(math.sqrt(len(panes)))
            panes = [
                'pane split_direction="vertical" {\n' + "\n".join(panes[index:index + columns]) + "\n}"
                for index in range(0, len(panes), columns)
            ]
        tabs.append(f"""tab name={_kdl_string(tab['tabName'])} split_direction="{direction}" {{
{chr(10).join(panes)}
}}""")
    return '''layout {
    default_tab_template {
        pane size=1 borderless=true {
            plugin location="zellij:tab-bar"
        }
        children
        pane size=2 borderless=true {
            plugin location="zellij:status-bar"
        }
    }
''' + "\n".join(tabs) + "\n}\n"


def wait_for_session(session_name: str) -> list[TabEntry]:
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if session_name in list_session_names():
            tabs = list_tab_entries(session_name)
            if tabs:
                return tabs
        time.sleep(STARTUP_POLL_SECONDS)
    raise ValueError(f"""Zellij session '{session_name}' did not become ready within {STARTUP_TIMEOUT_SECONDS:g} seconds.""")


def launch_session(session_name: str, layout: LayoutConfig, exit_mode: SessionExitMode) -> list[PaneEntry]:
    bootstrap_name = f"""stackops-starting-{uuid4().hex}"""
    with TemporaryDirectory(prefix="stackops-zellij-") as directory:
        layout_path = Path(directory) / "layout.kdl"
        layout_path.write_text(f"""layout {{
    tab name={_kdl_string(bootstrap_name)} {{
        pane command="bash" {{ args "--noprofile" "--norc" "-i"; }}
    }}
}}
""", encoding="utf-8")
        run_zellij(["--new-session-with-layout", str(layout_path), "attach", "--create-background", "--", session_name])
        bootstrap_tabs = wait_for_session(session_name)
    panes: list[PaneEntry] = []
    for tab in layout["layoutTabs"]:
        panes.extend(launch_tab(session_name=session_name, tab=tab, exit_mode=exit_mode))
    for tab in bootstrap_tabs:
        if tab.name == bootstrap_name:
            run_zellij(["--session", session_name, "action", "close-tab", "--tab-id", str(tab.tab_id)])
    return panes


def launch_tab(session_name: str, tab: TabConfig, exit_mode: SessionExitMode) -> list[PaneEntry]:
    existing_pane_ids = {pane.pane_id for pane in list_pane_entries(session_name)}
    run_zellij([
        "--session", session_name, "action", "new-tab", "--no-focus", "--layout-string",
        layout_kdl(layout={"layoutName": session_name, "layoutTabs": [tab]}, exit_mode=exit_mode),
    ])
    return [pane for pane in list_pane_entries(session_name) if pane.pane_id not in existing_pane_ids]
