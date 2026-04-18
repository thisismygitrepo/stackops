from datetime import datetime
from time import monotonic, sleep
from typing import Callable, Literal, TypeAlias

import typer
from rich import box
from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from stackops.scripts.python.helpers.helpers_sessions.session_trace_tmux import (
    PaneCategory,
    TracePaneState,
    TraceSnapshot,
    TraceUntil,
    build_missing_snapshot,
    evaluate_trace_snapshot,
    load_trace_snapshot as load_trace_snapshot_tmux,
)
from stackops.scripts.python.helpers.helpers_sessions.session_trace_zellij import (
    load_trace_snapshot as load_trace_snapshot_zellij,
)


TraceBackend: TypeAlias = Literal["tmux", "zellij"]
TraceSnapshotLoader: TypeAlias = Callable[[str, TraceUntil, int | None], TraceSnapshot]


_TRACE_LOADERS: dict[TraceBackend, TraceSnapshotLoader] = {
    "tmux": load_trace_snapshot_tmux,
    "zellij": load_trace_snapshot_zellij,
}


def _format_duration(seconds: float | None) -> str:
    if seconds is None:
        return "unknown"
    rounded_seconds = max(0, int(round(seconds)))
    hours, rem = divmod(rounded_seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def _checked_at_text() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


def _estimate_remaining_seconds(snapshot: TraceSnapshot, elapsed_seconds: float) -> float | None:
    if snapshot.criterion_satisfied:
        return 0.0
    if snapshot.total_targets <= 0 or snapshot.matched_targets <= 0:
        return None
    completion_ratio = snapshot.matched_targets / snapshot.total_targets
    if completion_ratio >= 1.0:
        return 0.0
    return elapsed_seconds * ((1.0 - completion_ratio) / completion_ratio)


def _render_progress_bar(total_targets: int, matched_targets: int) -> str:
    if total_targets <= 0:
        return "[························] waiting for observable targets"
    width = 24
    filled = int(round((matched_targets / total_targets) * width))
    empty = max(0, width - filled)
    percentage = (matched_targets / total_targets) * 100.0
    return f"[{'█' * filled}{'·' * empty}] {matched_targets}/{total_targets} ({percentage:.1f}%)"


def _criterion_label(until: TraceUntil, exit_code: int | None) -> str:
    match until:
        case "idle-shell":
            return "all panes idle shell"
        case "all-exited":
            return "all panes exited"
        case "exit-code":
            return f"all panes exited with code {exit_code}"
        case "session-missing":
            return "session missing"


def _session_state_label(snapshot: TraceSnapshot) -> str:
    if snapshot.criterion_satisfied:
        return "done"
    if snapshot.session_exists:
        return "active"
    return "missing"


def _build_overview_panel(
    snapshot: TraceSnapshot,
    until: TraceUntil,
    exit_code: int | None,
    attempt: int,
    elapsed_seconds: float,
    next_poll_seconds: float,
    checked_at_text: str,
) -> Panel:
    eta_seconds = _estimate_remaining_seconds(snapshot=snapshot, elapsed_seconds=elapsed_seconds)
    overview = Table.grid(expand=True)
    overview.add_column(style="bold cyan", ratio=1)
    overview.add_column(style="white", ratio=2)
    overview.add_column(style="bold cyan", ratio=1)
    overview.add_column(style="white", ratio=2)
    overview.add_row("Session", snapshot.session_name, "Criterion", _criterion_label(until=until, exit_code=exit_code))
    overview.add_row("State", _session_state_label(snapshot=snapshot), "Attempt", str(attempt))
    overview.add_row("Checked", checked_at_text, "Elapsed", _format_duration(elapsed_seconds))
    overview.add_row(
        "ETA",
        _format_duration(eta_seconds),
        "Next poll",
        "done" if snapshot.criterion_satisfied else f"{next_poll_seconds:0.1f}s",
    )
    overview.add_row(
        "Progress",
        _render_progress_bar(total_targets=snapshot.total_targets, matched_targets=snapshot.matched_targets),
        "Counts",
        (
            f"{snapshot.idle_shell_panes} idle, "
            f"{snapshot.running_panes} running, "
            f"{snapshot.exited_panes} exited, "
            f"{snapshot.unknown_panes} unknown"
        ),
    )
    overview.add_row(
        "Layout",
        f"{snapshot.total_windows} windows, {len(snapshot.panes)} panes",
        "Warnings",
        str(int(snapshot.pane_warning is not None or snapshot.session_error is not None)),
    )
    title = "Sessions Trace"
    border_style = "green" if snapshot.criterion_satisfied else "cyan"
    return Panel(overview, title=title, border_style=border_style, box=box.DOUBLE)


def _pane_row_style(pane: TracePaneState) -> str:
    if pane.matched:
        return "green"
    match pane.category:
        case "running":
            return "red"
        case "unknown":
            return "yellow"
        case "exited":
            return "magenta"
        case "idle-shell":
            return "cyan"


def _build_panes_table(snapshot: TraceSnapshot) -> Table:
    panes_table = Table(title="Pane State", box=box.SIMPLE_HEAVY, expand=True)
    panes_table.add_column("Win", justify="right", style="cyan", no_wrap=True)
    panes_table.add_column("Pane", justify="right", style="cyan", no_wrap=True)
    panes_table.add_column("Active", style="white", no_wrap=True)
    panes_table.add_column("Process", style="white")
    panes_table.add_column("Status", style="white")
    panes_table.add_column("Dir", style="dim")
    panes_table.add_column("Match", style="white", no_wrap=True)
    if len(snapshot.panes) == 0:
        panes_table.add_row("—", "—", "—", "—", "session has no observable panes yet", "—", "—")
        return panes_table

    for pane in snapshot.panes:
        panes_table.add_row(
            f"{pane.window_index}:{pane.window_name}",
            pane.pane_index,
            "yes" if pane.is_active else "",
            pane.process_name,
            pane.status_text,
            pane.cwd,
            "yes" if pane.matched else "",
            style=_pane_row_style(pane=pane),
        )
    return panes_table


def _build_warning_panel(snapshot: TraceSnapshot) -> Panel | None:
    warning_lines: list[str] = []
    if snapshot.session_error:
        warning_lines.append(f"session: {snapshot.session_error}")
    if snapshot.pane_warning:
        warning_lines.append(f"panes: {snapshot.pane_warning}")
    if len(warning_lines) == 0:
        return None
    return Panel("\n".join(warning_lines), title="Warnings", border_style="yellow")


def _build_trace_renderable(
    snapshot: TraceSnapshot,
    until: TraceUntil,
    exit_code: int | None,
    attempt: int,
    elapsed_seconds: float,
    next_poll_seconds: float,
    checked_at_text: str,
) -> RenderableType:
    renderables: list[RenderableType] = [
        _build_overview_panel(
            snapshot=snapshot,
            until=until,
            exit_code=exit_code,
            attempt=attempt,
            elapsed_seconds=elapsed_seconds,
            next_poll_seconds=next_poll_seconds,
            checked_at_text=checked_at_text,
        ),
        _build_panes_table(snapshot=snapshot),
    ]
    warning_panel = _build_warning_panel(snapshot=snapshot)
    if warning_panel is not None:
        renderables.append(warning_panel)
    return Group(*renderables)


def _validate_trace_options(until: TraceUntil, every_seconds: float, exit_code: int | None) -> None:
    if every_seconds <= 0:
        raise typer.BadParameter("`--every` must be greater than 0.")
    if until == "exit-code" and exit_code is None:
        raise typer.BadParameter("`--exit-code` is required when `--until exit-code` is selected.")
    if until != "exit-code" and exit_code is not None:
        raise typer.BadParameter("`--exit-code` can only be used together with `--until exit-code`.")


def trace_session_for_backend(
    backend: TraceBackend,
    session_name: str,
    until: TraceUntil,
    every_seconds: float,
    exit_code: int | None,
) -> None:
    _validate_trace_options(until=until, every_seconds=every_seconds, exit_code=exit_code)
    snapshot_loader = _TRACE_LOADERS[backend]
    console = Console()
    started_at = monotonic()
    attempt = 0
    try:
        with Live(
            _build_trace_renderable(
                snapshot=build_missing_snapshot(session_name=session_name, until=until, session_error=None),
                until=until,
                exit_code=exit_code,
                attempt=attempt,
                elapsed_seconds=0.0,
                next_poll_seconds=0.0,
                checked_at_text=_checked_at_text(),
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
                checked_at_text = _checked_at_text()
                live.update(
                    _build_trace_renderable(
                        snapshot=snapshot,
                        until=until,
                        exit_code=exit_code,
                        attempt=attempt,
                        elapsed_seconds=elapsed_seconds,
                        next_poll_seconds=every_seconds,
                        checked_at_text=checked_at_text,
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
                        _build_trace_renderable(
                            snapshot=snapshot,
                            until=until,
                            exit_code=exit_code,
                            attempt=attempt,
                            elapsed_seconds=monotonic() - started_at,
                            next_poll_seconds=remaining_seconds,
                            checked_at_text=checked_at_text,
                        )
                    )
        console.print(
            Panel(
                (
                    f"Session `{session_name}` satisfied `{_criterion_label(until=until, exit_code=exit_code)}` "
                    f"after {_format_duration(monotonic() - started_at)} and {attempt} checks."
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
