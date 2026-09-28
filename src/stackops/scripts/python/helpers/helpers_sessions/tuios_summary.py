from collections import Counter

import typer
from rich.console import Console
from rich.table import Table

from stackops.scripts.python.helpers.helpers_sessions._attach_common import interactive_choose_with_preview
from stackops.scripts.python.helpers.helpers_sessions._tuios_backend_idle import window_is_idle
from stackops.scripts.python.helpers.helpers_sessions._tuios_backend_models import SessionEntry
from stackops.scripts.python.helpers.helpers_sessions._tuios_backend_state import list_session_entries, list_window_entries


def _print_session_details(session: SessionEntry, console: Console) -> None:
    windows = list_window_entries(session_name=session.name)
    table = Table(title=f"""TUIOS: {session.name}""")
    for column in ("Window", "ID", "Workspace", "Focus", "Shell", "Agent", "Command", "Last exit", "CWD", "Host"):
        table.add_column(column, overflow="fold")
    for window in windows:
        idle = window_is_idle(session_name=session.name, window=window)
        table.add_row(
            window.display_name,
            window.window_id,
            str(window.workspace),
            "yes" if window.focused else "no",
            "idle" if idle is True else "running" if idle is False else "unknown",
            window.agent_state,
            window.running_command or window.foreground_command or "—",
            str(window.last_exit_code) if window.last_exit_code is not None else "—",
            window.cwd or "—",
            window.host or "local",
        )
    console.print(table)


def print_tuios_summary(session_name: str | None, choose_session: bool, show_tabs: bool) -> None:
    if session_name is not None and choose_session:
        raise typer.BadParameter("--session cannot be used together with --choose-session.")
    console = Console()
    try:
        sessions = [session for session in list_session_entries() if not session.saved]
        if choose_session:
            if not sessions:
                raise ValueError("No TUIOS sessions are available.")
            selected = interactive_choose_with_preview(
                msg="Choose a TUIOS session to summarize:",
                options_to_preview_mapping={
                    session.name: f"""TUIOS session: {session.name}\nWindows: {session.window_count}\nAttached: {session.attached}"""
                    for session in sessions
                },
            )
            if not isinstance(selected, str) or not selected:
                raise ValueError("No TUIOS session selected.")
            session_name = selected
        if session_name is not None:
            selected_session = next((session for session in sessions if session.name == session_name), None)
            if selected_session is None:
                raise ValueError(f"""TUIOS session '{session_name}' not found. Available sessions: {[session.name for session in sessions]}""")
            _print_session_details(session=selected_session, console=console)
            return
        table = Table(title=f"""TUIOS sessions ({len(sessions)})""")
        for column in ("Session", "Attached", "Workspaces", "Windows", "Idle", "Running", "Unknown", "Agents"):
            table.add_column(column)
        for session in sessions:
            windows = list_window_entries(session_name=session.name)
            idle_states = [window_is_idle(session_name=session.name, window=window) for window in windows]
            agents = Counter(window.agent_state for window in windows if window.agent_state != "none")
            table.add_row(
                session.name,
                "yes" if session.attached else "no",
                str(len({window.workspace for window in windows})),
                str(len(windows)),
                str(sum(idle is True for idle in idle_states)),
                str(sum(idle is False for idle in idle_states)),
                str(sum(idle is None for idle in idle_states)),
                ", ".join(f"""{state} x{count}""" for state, count in sorted(agents.items())) or "—",
            )
        console.print(table)
        if show_tabs:
            for session in sessions:
                _print_session_details(session=session, console=console)
    except ValueError as error:
        typer.echo(f"""Error: {error}""", err=True)
        raise typer.Exit(code=1) from error
