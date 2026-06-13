from typing import TYPE_CHECKING, Callable, Literal

import typer

if TYPE_CHECKING:
    from stackops.scripts.python.helpers.helpers_sessions.session_trace_tmux import (
        PaneCategory,
        TracePaneState,
        TraceSnapshot,
        TraceUntil,
        evaluate_trace_snapshot,
    )

type TraceBackend = Literal["tmux"]


def _get_trace_loader(
    backend: TraceBackend,
) -> Callable[[str, "TraceUntil", int | None], "TraceSnapshot"]:
    match backend:
        case "tmux":
            from stackops.scripts.python.helpers.helpers_sessions.session_trace_tmux import (
                load_trace_snapshot as loader,
            )
            return loader


def _validate_trace_options(
    until: "TraceUntil",
    every_seconds: float,
    exit_code: int | None,
) -> None:
    if every_seconds <= 0:
        raise typer.BadParameter("`--every` must be greater than 0.")
    if until == "exit-code" and exit_code is None:
        raise typer.BadParameter("`--exit-code` is required when `--until exit-code` is selected.")
    if until != "exit-code" and exit_code is not None:
        raise typer.BadParameter("`--exit-code` can only be used together with `--until exit-code`.")


def trace_session_for_backend(
    backend: TraceBackend,
    session_name: str,
    until: "TraceUntil",
    every_seconds: float,
    exit_code: int | None,
) -> None:
    from time import monotonic, sleep

    from rich.console import Console
    from rich.live import Live
    from rich.panel import Panel

    from stackops.scripts.python.helpers.helpers_sessions.session_trace_tmux import (
        build_missing_snapshot,
    )
    from stackops.scripts.python.helpers.helpers_sessions.sessions_trace_render import (
        build_trace_renderable,
        checked_at_text,
        criterion_label,
        format_duration,
    )

    _validate_trace_options(until=until, every_seconds=every_seconds, exit_code=exit_code)
    snapshot_loader = _get_trace_loader(backend=backend)
    console = Console()
    started_at = monotonic()
    attempt = 0
    try:
        with Live(
            build_trace_renderable(
                snapshot=build_missing_snapshot(session_name=session_name, until=until, session_error=None),
                until=until,
                exit_code=exit_code,
                attempt=attempt,
                elapsed_seconds=0.0,
                next_poll_seconds=0.0,
                checked_at=checked_at_text(),
            ),
            console=console,
            refresh_per_second=8,
            transient=False,
        ) as live:
            while True:
                attempt += 1
                try:
                    snapshot = snapshot_loader(session_name, until, exit_code)
                except NotImplementedError as exc:
                    raise typer.BadParameter(str(exc)) from exc
                elapsed_seconds = monotonic() - started_at
                current_checked_at = checked_at_text()
                live.update(
                    build_trace_renderable(
                        snapshot=snapshot,
                        until=until,
                        exit_code=exit_code,
                        attempt=attempt,
                        elapsed_seconds=elapsed_seconds,
                        next_poll_seconds=every_seconds,
                        checked_at=current_checked_at,
                    )
                )
                if snapshot.criterion_satisfied:
                    break
                remaining_seconds = every_seconds
                while remaining_seconds > 0:
                    sleep_step = min(1.0, remaining_seconds)
                    sleep(sleep_step)
                    remaining_seconds -= sleep_step
                    live.update(
                        build_trace_renderable(
                            snapshot=snapshot,
                            until=until,
                            exit_code=exit_code,
                            attempt=attempt,
                            elapsed_seconds=monotonic() - started_at,
                            next_poll_seconds=remaining_seconds,
                            checked_at=current_checked_at,
                        )
                    )
        console.print(
            Panel(
                (
                    f"Session `{session_name}` satisfied `{criterion_label(until=until, exit_code=exit_code)}` "
                    f"after {format_duration(monotonic() - started_at)} and {attempt} checks."
                ),
                title="Complete",
                border_style="green",
            )
        )
    except KeyboardInterrupt as exc:
        console.print(Panel("Trace interrupted by user.", title="Interrupted", border_style="red"))
        raise typer.Exit(code=130) from exc


def trace_session(
    session_name: str,
    until: "TraceUntil",
    every_seconds: float,
    exit_code: int | None,
) -> None:
    trace_session_for_backend(
        backend="tmux",
        session_name=session_name,
        until=until,
        every_seconds=every_seconds,
        exit_code=exit_code,
    )


__all__: list[str] = [
    "PaneCategory",
    "TracePaneState",
    "TraceSnapshot",
    "TraceUntil",
    "TraceBackend",
    "evaluate_trace_snapshot",
    "trace_session",
    "trace_session_for_backend",
]


def __getattr__(name: str) -> object:
    if name in {"PaneCategory", "TracePaneState", "TraceSnapshot", "TraceUntil", "evaluate_trace_snapshot"}:
        from stackops.scripts.python.helpers.helpers_sessions import session_trace_tmux
        return getattr(session_trace_tmux, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
