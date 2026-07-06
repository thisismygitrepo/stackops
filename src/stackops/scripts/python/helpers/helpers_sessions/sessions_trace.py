from collections.abc import Callable

import typer

from stackops.scripts.python.helpers.helpers_sessions.session_trace_models import (
    PaneCategory,
    TraceBackend,
    TraceBackendOption,
    TracePaneState,
    TraceSnapshot,
    TraceUntil,
)


def resolve_trace_backend(backend: TraceBackendOption) -> TraceBackend:
    import platform

    match backend:
        case "tmux" | "t":
            return "tmux"
        case "herdr" | "h":
            if platform.system().lower() == "windows":
                typer.echo("Error: Herdr is not supported on Windows.", err=True, color=True)
                raise typer.Exit(code=1)
            return "herdr"
        case "aoe" | "a" | "e":
            if platform.system().lower() == "windows":
                typer.echo("Error: AoE is not supported on Windows.", err=True, color=True)
                raise typer.Exit(code=1)
            return "aoe"
        case _:
            typer.echo(f"Error: Unsupported backend '{backend}'.", err=True, color=True)
            raise typer.Exit(code=1)


def _get_trace_loader(
    backend: TraceBackend,
) -> Callable[[str, TraceUntil, int | None], TraceSnapshot]:
    match backend:
        case "tmux":
            from stackops.scripts.python.helpers.helpers_sessions.session_trace_tmux import (
                load_trace_snapshot as loader,
            )
            return loader
        case "herdr":
            from stackops.scripts.python.helpers.helpers_sessions.session_trace_herdr import (
                load_trace_snapshot as loader,
            )
            return loader
        case "aoe":
            from stackops.scripts.python.helpers.helpers_sessions.session_trace_aoe import (
                load_trace_snapshot as loader,
            )
            return loader


def _validate_trace_options(
    until: TraceUntil,
    every_seconds: float,
    exit_code: int | None,
) -> None:
    if every_seconds <= 0:
        raise typer.BadParameter("`--every` must be greater than 0.")
    if until == "exit-code" and exit_code is None:
        raise typer.BadParameter("`--exit-code` is required when `--until exit-code` is selected.")
    if until != "exit-code" and exit_code is not None:
        raise typer.BadParameter("`--exit-code` can only be used together with `--until exit-code`.")


def trace_sessions_for_backend(
    backend: TraceBackend,
    session_names: list[str],
    until: TraceUntil,
    every_seconds: float,
    exit_code: int | None,
    kill: bool,
) -> None:
    _validate_trace_options(until=until, every_seconds=every_seconds, exit_code=exit_code)
    if len(session_names) == 0:
        raise typer.BadParameter("At least one session must be selected.")
    if len(session_names) != len(set(session_names)):
        raise typer.BadParameter("Selected session names must be unique.")

    from stackops.scripts.python.helpers.helpers_sessions.session_trace_runner import (
        trace_sessions,
    )

    trace_sessions(
        backend=backend,
        session_names=session_names,
        until=until,
        every_seconds=every_seconds,
        exit_code=exit_code,
        kill=kill,
        snapshot_loader=_get_trace_loader(backend=backend),
    )


def trace_session_for_backend(
    backend: TraceBackend,
    session_name: str,
    until: TraceUntil,
    every_seconds: float,
    exit_code: int | None,
) -> None:
    trace_sessions_for_backend(
        backend=backend,
        session_names=[session_name],
        until=until,
        every_seconds=every_seconds,
        exit_code=exit_code,
        kill=False,
    )


def trace_session(
    session_name: str,
    until: TraceUntil,
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


def evaluate_trace_snapshot(
    session_name: str,
    windows: list[dict[str, str]],
    panes_by_window: dict[str, list[dict[str, str]]],
    until: TraceUntil,
    expected_exit_code: int | None,
    pane_warning: str | None,
) -> TraceSnapshot:
    from stackops.scripts.python.helpers.helpers_sessions.session_trace_tmux import (
        evaluate_trace_snapshot as impl,
    )

    return impl(
        session_name=session_name,
        windows=windows,
        panes_by_window=panes_by_window,
        until=until,
        expected_exit_code=expected_exit_code,
        pane_warning=pane_warning,
    )


__all__: list[str] = [
    "PaneCategory",
    "TracePaneState",
    "TraceSnapshot",
    "TraceUntil",
    "TraceBackend",
    "TraceBackendOption",
    "evaluate_trace_snapshot",
    "resolve_trace_backend",
    "trace_session",
    "trace_session_for_backend",
    "trace_sessions_for_backend",
]


def __getattr__(name: str) -> object:
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
