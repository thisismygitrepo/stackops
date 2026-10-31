import typer
from rich.console import Console
from rich.table import Table

from stackops.scripts.python.helpers.helpers_sessions._attach_common import interactive_choose_with_preview
from stackops.scripts.python.helpers.helpers_sessions._zellij_backend_state import list_session_names
from stackops.scripts.python.helpers.helpers_sessions.session_trace_models import TraceSnapshot
from stackops.scripts.python.helpers.helpers_sessions.session_trace_zellij import load_trace_snapshot


def _load_snapshot(session_name: str) -> TraceSnapshot:
    snapshot = load_trace_snapshot(session_name=session_name, until="idle-shell", expected_exit_code=None)
    if snapshot.session_error or snapshot.pane_warning:
        raise ValueError(snapshot.session_error or snapshot.pane_warning)
    return snapshot


def _print_session_details(snapshot: TraceSnapshot, console: Console) -> None:
    table = Table(title=f"""Zellij: {snapshot.session_name}""", highlight=False)
    for column in ("Tab", "Tab ID", "Pane", "Focus", "Status", "Command", "Exit", "CWD"):
        table.add_column(column, overflow="fold")
    for pane in snapshot.panes:
        table.add_row(
            pane.window_name,
            pane.window_target,
            pane.pane_target,
            "yes" if pane.is_active else "no",
            pane.status_text,
            pane.process_name,
            str(pane.exit_code) if pane.exit_code is not None else "—",
            pane.cwd,
        )
    console.print(table)


def print_zellij_summary(session_name: str | None, choose_session: bool, show_tabs: bool) -> None:
    if session_name is not None and choose_session:
        raise typer.BadParameter("--session cannot be used together with --choose-session.")
    console = Console()
    try:
        names = list_session_names()
        if choose_session:
            from stackops.scripts.python.helpers.helpers_sessions._zellij_backend import get_session_preview

            if not names:
                raise ValueError("No Zellij sessions are available.")
            selected = interactive_choose_with_preview(
                msg="Choose a Zellij session to summarize:",
                options_to_preview_mapping={name: get_session_preview(name) for name in names},
                multi=False,
            )
            if not isinstance(selected, str) or not selected:
                raise ValueError("No Zellij session selected.")
            session_name = selected
        if session_name is not None:
            if session_name not in names:
                raise ValueError(f"""Zellij session '{session_name}' not found. Available sessions: {names}""")
            _print_session_details(snapshot=_load_snapshot(session_name=session_name), console=console)
            return
        snapshots = [_load_snapshot(session_name=name) for name in names]
        table = Table(title=f"""Zellij sessions ({len(names)})""", highlight=False)
        for column in ("Session", "Tabs", "Panes", "Idle", "Running", "Exited", "Unknown"):
            table.add_column(column)
        for snapshot in snapshots:
            table.add_row(
                snapshot.session_name,
                str(snapshot.total_windows),
                str(len(snapshot.panes)),
                str(snapshot.idle_shell_panes),
                str(snapshot.running_panes),
                str(snapshot.exited_panes),
                str(snapshot.unknown_panes),
            )
        console.print(table)
        if show_tabs:
            for snapshot in snapshots:
                _print_session_details(snapshot=snapshot, console=console)
    except ValueError as error:
        typer.echo(f"""Error: {error}""", err=True)
        raise typer.Exit(code=1) from error
