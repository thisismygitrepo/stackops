from collections.abc import Callable

import typer

from stackops.scripts.python.helpers.helpers_sessions.kill_models import KilledTarget
from stackops.scripts.python.helpers.helpers_sessions.session_trace_kill import (
    build_trace_kill_plan,
    execute_trace_kill_plan,
)
from stackops.scripts.python.helpers.helpers_sessions.session_trace_models import (
    TraceBackend,
    TraceSnapshot,
    TraceUntil,
    build_missing_snapshot,
)


type TraceSnapshotLoader = Callable[[str, TraceUntil, int | None], TraceSnapshot]


def trace_sessions(
    backend: TraceBackend,
    session_names: list[str],
    until: TraceUntil,
    every_seconds: float,
    exit_code: int | None,
    kill: bool,
    snapshot_loader: TraceSnapshotLoader,
) -> None:
    from time import monotonic, sleep

    from rich.console import Console, Group
    from rich.live import Live
    from rich.panel import Panel
    from rich.text import Text

    from stackops.scripts.python.helpers.helpers_sessions.sessions_trace_render import (
        build_traces_renderable,
        checked_at_text,
        criterion_label,
        format_duration,
    )

    console = Console()
    started_at = monotonic()
    attempt = 0
    completed_session_names: set[str] = set()
    killed_targets: list[KilledTarget] = []
    latest_snapshot_by_name = {
        session_name: build_missing_snapshot(
            session_name=session_name,
            until=until,
            session_error=None,
        )
        for session_name in session_names
    }
    snapshots = tuple(latest_snapshot_by_name.values())

    try:
        with Live(
            build_traces_renderable(
                snapshots=snapshots,
                backend=backend,
                until=until,
                exit_code=exit_code,
                attempt=attempt,
                elapsed_seconds=0.0,
                next_poll_seconds=0.0,
                checked_at=checked_at_text(),
                console=console,
            ),
            console=console,
            refresh_per_second=8,
            transient=False,
        ) as live:
            while True:
                attempt += 1
                active_session_names = [
                    session_name
                    for session_name in session_names
                    if session_name not in completed_session_names
                ]
                try:
                    active_snapshots = tuple(
                        snapshot_loader(session_name, until, exit_code)
                        for session_name in active_session_names
                    )
                except NotImplementedError as error:
                    raise typer.BadParameter(str(error)) from error

                for session_name, snapshot in zip(
                    active_session_names,
                    active_snapshots,
                    strict=True,
                ):
                    if snapshot.session_name != session_name:
                        raise typer.BadParameter(
                            f"Trace loader returned '{snapshot.session_name}' for requested session '{session_name}'."
                        )
                    latest_snapshot_by_name[snapshot.session_name] = snapshot
                snapshots = tuple(
                    latest_snapshot_by_name[session_name]
                    for session_name in session_names
                )
                elapsed_seconds = monotonic() - started_at
                current_checked_at = checked_at_text()
                live.update(
                    build_traces_renderable(
                        snapshots=snapshots,
                        backend=backend,
                        until=until,
                        exit_code=exit_code,
                        attempt=attempt,
                        elapsed_seconds=elapsed_seconds,
                        next_poll_seconds=every_seconds,
                        checked_at=current_checked_at,
                        console=console,
                    )
                )

                if kill:
                    try:
                        kill_plan = build_trace_kill_plan(
                            backend=backend,
                            snapshots=active_snapshots,
                        )
                        execute_trace_kill_plan(plan=kill_plan)
                    except (RuntimeError, ValueError) as error:
                        raise typer.BadParameter(str(error)) from error
                    killed_targets.extend(command.summary for command in kill_plan.commands)
                    completed_session_names.update(kill_plan.completed_session_names)
                    if len(completed_session_names) == len(session_names):
                        break
                elif all(snapshot.criterion_satisfied for snapshot in snapshots):
                    break

                remaining_seconds = every_seconds
                while remaining_seconds > 0:
                    sleep_step = min(1.0, remaining_seconds)
                    sleep(sleep_step)
                    remaining_seconds -= sleep_step
                    live.update(
                        build_traces_renderable(
                            snapshots=snapshots,
                            backend=backend,
                            until=until,
                            exit_code=exit_code,
                            attempt=attempt,
                            elapsed_seconds=monotonic() - started_at,
                            next_poll_seconds=remaining_seconds,
                            checked_at=current_checked_at,
                            console=console,
                        )
                    )

        selected_targets = "\n".join(f"  {session_name}" for session_name in session_names)
        target_noun = "Session" if len(session_names) == 1 else "Sessions"
        summary_content = Group(
            Text.assemble(
                (f"{target_noun} satisfied ", "white"),
                (criterion_label(until=until, exit_code=exit_code), "bold cyan"),
                (f" after {format_duration(monotonic() - started_at)} and {attempt} checks.", "white"),
            ),
            Text(selected_targets, style="white"),
        )
        console.print(
            Panel(
                summary_content,
                title="Complete",
                border_style="green",
            )
        )
        if len(killed_targets) > 0:
            from stackops.scripts.python.helpers.helpers_sessions.terminal_cli_helpers import (
                print_kill_summary,
            )

            print_kill_summary(script="", killed_targets=killed_targets)
    except KeyboardInterrupt as error:
        console.print(Panel("Trace interrupted by user.", title="Interrupted", border_style="red"))
        raise typer.Exit(code=130) from error
