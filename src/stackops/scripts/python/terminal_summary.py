"""Print running terminal session summaries."""

from collections import Counter
from dataclasses import dataclass
from typing import Annotated, Literal, TypeAlias

import typer


PaneCategory: TypeAlias = Literal["idle", "running", "exited", "unknown"]


@dataclass(frozen=True)
class SessionSummary:
    name: str
    windows: int
    panes: int
    processes: int
    idle_shells: int
    running: int
    exited: int
    unknown: int
    idle_panes: str
    process_names: str


def _pane_category(status: str) -> PaneCategory:
    if status == "idle shell":
        return "idle"
    if status.startswith("running:"):
        return "running"
    if status.startswith("exited ("):
        return "exited"
    return "unknown"


def _process_group_name(process_name: str) -> str:
    text = process_name.strip().strip("`")
    if text == "" or text == "—":
        return "—"
    return text.split(maxsplit=1)[0]


def _format_process_names(process_counts: Counter[str]) -> str:
    if not process_counts:
        return "—"
    rows = sorted(process_counts.items(), key=lambda item: (-item[1], item[0]))
    return ", ".join(f"{name} x{count}" if count > 1 else name for name, count in rows)


def _collect_tmux_summary(session_name: str) -> SessionSummary:
    from stackops.scripts.python.helpers.helpers_sessions._attach_common import run_command
    from stackops.scripts.python.helpers.helpers_sessions._tmux_backend import classify_pane_status
    from stackops.scripts.python.helpers.helpers_sessions._tmux_backend_preview import collect_session_snapshot

    windows, panes_by_window, pane_warning = collect_session_snapshot(
        session_name=session_name,
        run_command_fn=run_command,
    )
    if windows is None:
        return SessionSummary(
            name=session_name,
            windows=0,
            panes=0,
            processes=0,
            idle_shells=0,
            running=0,
            exited=0,
            unknown=1,
            idle_panes="—",
            process_names=pane_warning or "unavailable",
        )

    category_counts: Counter[PaneCategory] = Counter()
    process_counts: Counter[str] = Counter()
    idle_panes: list[str] = []
    panes = 0
    for window in windows:
        for pane in panes_by_window.get(window["window_index"], []):
            process_name, status = classify_pane_status(pane=pane)
            category = _pane_category(status=status)
            category_counts[category] += 1
            panes += 1
            if category == "idle":
                idle_panes.append(f"{window['window_index']}.{pane['pane_index']}")
            if category == "running":
                process_counts[_process_group_name(process_name=process_name)] += 1

    return SessionSummary(
        name=session_name,
        windows=len(windows),
        panes=panes,
        processes=sum(process_counts.values()),
        idle_shells=category_counts["idle"],
        running=category_counts["running"],
        exited=category_counts["exited"],
        unknown=category_counts["unknown"],
        idle_panes=", ".join(idle_panes) if idle_panes else "—",
        process_names=_format_process_names(process_counts=process_counts),
    )


def _print_tmux_summary() -> None:
    from rich import box
    from rich.console import Console
    from rich.table import Table
    from stackops.scripts.python.helpers.helpers_sessions._tmux_backend import list_session_names

    console = Console()
    session_names = list_session_names()
    table = Table(
        title=f"tmux sessions ({len(session_names)})",
        box=box.SIMPLE_HEAVY,
        show_lines=False,
    )
    table.add_column("Session", style="bold cyan")
    table.add_column("Win", justify="right")
    table.add_column("Panes", justify="right")
    table.add_column("Proc", justify="right", style="green")
    table.add_column("Idle", justify="right", style="yellow")
    table.add_column("Run", justify="right", style="green")
    table.add_column("Exit", justify="right", style="red")
    table.add_column("Unk", justify="right", style="magenta")
    table.add_column("Idle Panes", overflow="fold")
    table.add_column("Process Names", overflow="fold")

    for session in [_collect_tmux_summary(session_name=name) for name in session_names]:
        table.add_row(
            session.name,
            str(session.windows),
            str(session.panes),
            str(session.processes),
            str(session.idle_shells),
            str(session.running),
            str(session.exited),
            str(session.unknown),
            session.idle_panes,
            session.process_names,
        )
    console.print(table)


def _print_tmux_session_details(session_name: str) -> None:
    from rich.console import Console
    from rich.markdown import Markdown
    from stackops.scripts.python.helpers.helpers_sessions._attach_common import run_command
    from stackops.scripts.python.helpers.helpers_sessions._tmux_backend import classify_pane_status
    from stackops.scripts.python.helpers.helpers_sessions._tmux_backend_preview import build_preview

    preview = build_preview(
        session_name=session_name,
        run_command_fn=run_command,
        classify_pane_status_fn=classify_pane_status,
    )
    Console().print(Markdown(preview))


def _resolve_tmux_session_name(session_name: str | None, choose_session: bool) -> str | None:
    from stackops.scripts.python.helpers.helpers_sessions._tmux_backend import (
        choose_existing_session_name,
        list_session_names,
    )

    if session_name is not None and choose_session:
        typer.echo("Error: --session cannot be used together with --choose-session.", err=True, color=True)
        raise typer.Exit(code=1)
    if choose_session:
        action, payload = choose_existing_session_name(msg="Choose a tmux session to summarize:")
        if action != "session_name":
            typer.echo(f"Error: {payload}", err=True, color=True)
            raise typer.Exit(code=1)
        return payload
    if session_name is None:
        return None

    available_sessions = list_session_names()
    if session_name not in available_sessions:
        available = ", ".join(available_sessions) if available_sessions else "none"
        typer.echo(
            f"Error: tmux session '{session_name}' not found. Available sessions: {available}",
            err=True,
            color=True,
        )
        raise typer.Exit(code=1)
    return session_name


def summary(
    backend: Annotated[Literal["tmux", "t"], typer.Option("--backend", "-b", help="Backend to summarize.")] = "tmux",
    session: Annotated[str | None, typer.Option("--session", "-s", help="Show details for one session by name.")] = None,
    choose_session: Annotated[bool, typer.Option("--choose-session", "-c", help="Choose one session interactively and show details.")] = False,
) -> None:
    """Print running terminal session summaries or details for one session."""
    match backend:
        case "tmux" | "t":
            session_name = _resolve_tmux_session_name(session_name=session, choose_session=choose_session)
            if session_name is None:
                _print_tmux_summary()
                return
            _print_tmux_session_details(session_name=session_name)
