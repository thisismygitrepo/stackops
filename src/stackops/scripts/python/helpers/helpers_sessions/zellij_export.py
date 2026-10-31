from stackops.scripts.python.helpers.helpers_sessions._zellij_backend import choose_existing_session_names
from stackops.scripts.python.helpers.helpers_sessions._zellij_backend_idle import pane_is_idle
from stackops.scripts.python.helpers.helpers_sessions._zellij_backend_models import PaneEntry
from stackops.scripts.python.helpers.helpers_sessions._zellij_backend_state import (
    list_pane_entries,
    list_session_names,
    list_tab_entries,
)
from stackops.scripts.python.helpers.helpers_sessions.sessions_zellij_commands import original_command, original_start_dir
from stackops.scripts.python.helpers.helpers_sessions.tmux_export_constants import (
    TMUX_EXPORT_SHELL_COMMAND,
    TmuxExportCommandSource,
)
from stackops.utils.schemas.layouts.layout_arrangement import infer_arrangement_from_origins
from stackops.utils.schemas.layouts.layout_types import LayoutConfig, PaneConfig, TabConfig


def resolve_zellij_sessions_for_export(session_names: str | None, export_all_sessions: bool) -> list[str]:
    if export_all_sessions and session_names is not None:
        raise ValueError("--all cannot be used together with --sessions.")
    available_names = list_session_names()
    if not available_names:
        raise ValueError("No Zellij sessions are available to export.")
    if export_all_sessions:
        return available_names
    if session_names is None or not session_names.strip():
        _action, selection = choose_existing_session_names(msg="Choose Zellij sessions to export:")
        if isinstance(selection, str):
            raise ValueError(selection)
        return selection
    requested_names = list(dict.fromkeys(name.strip() for name in session_names.split(",")))
    missing_names = [name for name in requested_names if name not in available_names]
    if missing_names:
        raise ValueError(f"""Unknown Zellij sessions: {missing_names}. Available sessions: {available_names}""")
    return requested_names


def _unique_name(name: str, used_names: set[str]) -> str:
    unique_name = name
    suffix = 2
    while unique_name in used_names:
        unique_name = f"""{name}-{suffix}"""
        suffix += 1
    used_names.add(unique_name)
    return unique_name


def _export_pane(pane: PaneEntry, used_names: set[str], command_source: TmuxExportCommandSource) -> PaneConfig:
    name = _unique_name(name=pane.title or pane.pane_id, used_names=used_names)
    start_dir = pane.cwd or original_start_dir(terminal_command=pane.terminal_command)
    if not start_dir:
        raise ValueError(f"""Zellij pane '{name}' does not report its working directory.""")
    match command_source:
        case "shell":
            command = TMUX_EXPORT_SHELL_COMMAND
        case "start-command":
            command = original_command(terminal_command=pane.terminal_command) if pane.terminal_command else TMUX_EXPORT_SHELL_COMMAND
        case "current-command":
            if pane.exited or pane_is_idle(pane=pane) is True:
                command = TMUX_EXPORT_SHELL_COMMAND
            elif pane.command:
                command = original_command(terminal_command=pane.command)
            else:
                raise ValueError(f"""Zellij pane '{name}' does not report its running command. Use --command-source shell or start-command.""")
    return {"paneName": name, "startDir": start_dir, "command": command}


def build_layouts_from_zellij_sessions(session_names: list[str], command_source: TmuxExportCommandSource) -> list[LayoutConfig]:
    if not session_names:
        raise ValueError("No Zellij sessions were selected for export.")
    layouts: list[LayoutConfig] = []
    for session_name in session_names:
        tabs = list_tab_entries(session_name=session_name)
        if not tabs:
            raise ValueError(f"""Zellij session '{session_name}' has no tabs to export.""")
        panes = list_pane_entries(session_name=session_name)
        exported_tabs: list[TabConfig] = []
        used_tab_names: set[str] = set()
        for tab in tabs:
            tab_panes = [pane for pane in panes if pane.tab_id == tab.tab_id]
            if not tab_panes:
                raise ValueError(f"""Zellij tab '{tab.name}' in session '{session_name}' has no terminal panes to export.""")
            used_pane_names: set[str] = set()
            exported_tab: TabConfig = {
                "tabName": _unique_name(name=tab.name or f"""tab-{tab.position}""", used_names=used_tab_names),
                "panes": [
                    _export_pane(pane=pane, used_names=used_pane_names, command_source=command_source)
                    for pane in sorted(tab_panes, key=lambda pane: (pane.y, pane.x))
                ],
            }
            if len(tab_panes) > 1:
                exported_tab["arrangement"] = infer_arrangement_from_origins(origins=[(pane.x, pane.y) for pane in tab_panes])
            exported_tabs.append(exported_tab)
        layouts.append({"layoutName": session_name, "layoutTabs": exported_tabs})
    return layouts
