"""Shared helpers for terminal CLI commands."""

import subprocess

import typer

from stackops.scripts.python.helpers.helpers_sessions.kill_models import KilledTarget
from stackops.utils.schemas.config.multiplexer_types import SessionMultiplexer, SessionMultiplexerOption


def run_detached_shell_script(script: str) -> None:
    if script.strip() == "":
        raise ValueError("Detached shell script must not be empty.")
    _process = subprocess.Popen(
        ("sh", "-c", script),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def parse_tmux_target(target: str) -> tuple[str, str, str]:
    if target.startswith("%"):
        return (f"(id {target})", "-", "-")
    if ":" in target:
        session, _, rest = target.partition(":")
        if "." in rest:
            window, _, pane = rest.partition(".")
            return (session, window, pane)
        return (session, rest, "-")
    return (target, "-", "-")


def print_kill_summary(
    script: str,
    killed_targets: list[KilledTarget],
) -> None:
    import re
    from rich import box
    from rich.console import Console
    from rich.table import Table

    rows: list[tuple[str, str, str, str]] = []
    if killed_targets:
        for target in killed_targets:
            rows.append((target["action"], target["session"], target["window"], target["detail"]))
    else:
        for line in script.splitlines():
            line = line.strip()
            if match := re.match(r"tmux kill-session\s+-t\s+(.+)", line):
                target = match.group(1).strip("'\"")
                rows.append(("session", target, "-", "-"))
            elif match := re.match(r"tmux kill-window\s+-t\s+(.+)", line):
                target = match.group(1).strip("'\"")
                session, window, _ = parse_tmux_target(target)
                rows.append(("window", session, window, "-"))
            elif match := re.match(r"tmux kill-pane\s+-t\s+(.+)", line):
                target = match.group(1).strip("'\"")
                session, window, pane = parse_tmux_target(target)
                rows.append(("pane", session, window, pane))
    if not rows:
        return
    console = Console()
    table = Table(title="Killed", box=box.SIMPLE, header_style="bold cyan")
    table.add_column("Action", style="bold")
    table.add_column("Session", style="magenta")
    table.add_column("Window", style="green")
    table.add_column("Detail")
    for action, session, window, detail in rows:
        table.add_row(action, session, window, detail)
    console.print(table)


def resolve_session_backend(backend: SessionMultiplexerOption | None) -> SessionMultiplexer:
    from stackops.utils.default_multiplexer import resolve_session_multiplexer

    try:
        return resolve_session_multiplexer(multiplexer=backend)
    except ValueError as error:
        typer.echo(f"Error: {error}", err=True, color=True)
        raise typer.Exit(code=1) from error
