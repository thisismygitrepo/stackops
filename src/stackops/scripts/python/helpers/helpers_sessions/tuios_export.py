from stackops.scripts.python.helpers.helpers_sessions._tuios_backend import choose_existing_session_names
from stackops.scripts.python.helpers.helpers_sessions._tuios_backend_state import list_session_entries, list_window_entries
from stackops.scripts.python.helpers.helpers_sessions.tmux_export_constants import (
    TMUX_EXPORT_SHELL_COMMAND,
    TmuxExportCommandSource,
)
from stackops.utils.schemas.layouts.layout_types import LayoutConfig, TabConfig


def resolve_tuios_sessions_for_export(session_names: str | None, export_all_sessions: bool) -> list[str]:
    if export_all_sessions and session_names is not None:
        raise ValueError("--all cannot be used together with --sessions.")
    available_names = [session.name for session in list_session_entries() if not session.saved]
    if not available_names:
        raise ValueError("No TUIOS sessions are available to export.")
    if export_all_sessions:
        return available_names
    if session_names is None or not session_names.strip():
        _action, selection = choose_existing_session_names(msg="Choose TUIOS sessions to export:")
        if isinstance(selection, str):
            raise ValueError(selection)
        return selection
    requested_names = list(dict.fromkeys(name.strip() for name in session_names.split(",")))
    missing_names = [name for name in requested_names if name not in available_names]
    if missing_names:
        raise ValueError(f"""Unknown TUIOS sessions: {missing_names}. Available sessions: {available_names}""")
    return requested_names


def build_layouts_from_tuios_sessions(session_names: list[str], command_source: TmuxExportCommandSource) -> list[LayoutConfig]:
    if command_source == "start-command":
        raise ValueError("TUIOS does not expose window start commands. Use --command-source shell or current-command.")
    layouts: list[LayoutConfig] = []
    for session_name in session_names:
        windows = list_window_entries(session_name=session_name)
        if not windows:
            raise ValueError(f"""TUIOS session '{session_name}' has no windows to export.""")
        tabs: list[TabConfig] = []
        used_names: set[str] = set()
        for window in windows:
            name = window.display_name or f"""window-{window.index}"""
            base_name = name
            suffix = 2
            while name in used_names:
                name = f"""{base_name}-{suffix}"""
                suffix += 1
            used_names.add(name)
            if not window.cwd:
                raise ValueError(f"""TUIOS window '{name}' does not report its working directory. Enable shell integration before exporting.""")
            command = TMUX_EXPORT_SHELL_COMMAND
            if command_source == "current-command":
                command = window.running_command or window.foreground_command
                if not command:
                    if window.at_prompt is True:
                        command = TMUX_EXPORT_SHELL_COMMAND
                    else:
                        raise ValueError(f"""TUIOS window '{name}' does not report its running command. Use --command-source shell.""")
            tabs.append({"tabName": name, "startDir": window.cwd, "command": command})
        layouts.append({"layoutName": session_name, "layoutTabs": tabs})
    return layouts
