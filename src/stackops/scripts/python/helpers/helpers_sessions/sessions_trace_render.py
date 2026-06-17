from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.console import RenderableType
    from rich.panel import Panel
    from rich.table import Table
    from stackops.scripts.python.helpers.helpers_sessions.session_trace_models import (
        TracePaneState,
        TraceSnapshot,
        TraceUntil,
    )


def format_duration(seconds: float | None) -> str:
    if seconds is None:
        return "unknown"
    rounded_seconds = max(0, int(round(seconds)))
    hours, rem = divmod(rounded_seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"

def checked_at_text() -> str:
    from datetime import datetime
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")

def _estimate_remaining_seconds(snapshot: "TraceSnapshot", elapsed_seconds: float) -> float | None:
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

def criterion_label(until: "TraceUntil", exit_code: int | None) -> str:
    match until:
        case "idle-shell":
            return "all panes idle shell"
        case "all-exited":
            return "all panes exited"
        case "exit-code":
            return f"all panes exited with code {exit_code}"
        case "session-missing":
            return "session missing"

def _session_state_label(snapshot: "TraceSnapshot") -> str:
    if snapshot.criterion_satisfied:
        return "done"
    if snapshot.session_exists:
        return "active"
    return "missing"

def _pane_row_style(pane: "TracePaneState") -> str:
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

def _build_overview_panel(
    snapshot: "TraceSnapshot",
    until: "TraceUntil",
    exit_code: int | None,
    attempt: int,
    elapsed_seconds: float,
    next_poll_seconds: float,
    checked_at: str,
) -> "Panel":
    from rich import box
    from rich.panel import Panel
    from rich.table import Table

    eta_seconds = _estimate_remaining_seconds(snapshot=snapshot, elapsed_seconds=elapsed_seconds)
    overview = Table.grid(expand=True)
    overview.add_column(style="bold cyan", ratio=1)
    overview.add_column(style="white", ratio=2)
    overview.add_column(style="bold cyan", ratio=1)
    overview.add_column(style="white", ratio=2)
    overview.add_row("Session", snapshot.session_name, "Criterion", criterion_label(until=until, exit_code=exit_code))
    overview.add_row("State", _session_state_label(snapshot=snapshot), "Attempt", str(attempt))
    overview.add_row("Checked", checked_at, "Elapsed", format_duration(elapsed_seconds))
    overview.add_row(
        "ETA",
        format_duration(eta_seconds),
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
    return Panel(
        overview,
        title="Sessions Trace",
        border_style="green" if snapshot.criterion_satisfied else "cyan",
        box=box.DOUBLE,
    )

def _build_panes_table(snapshot: "TraceSnapshot") -> "Table":
    from rich import box
    from rich.table import Table

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

def _build_warning_panel(snapshot: "TraceSnapshot") -> "Panel | None":
    from rich.panel import Panel

    warning_lines: list[str] = []
    if snapshot.session_error:
        warning_lines.append(f"session: {snapshot.session_error}")
    if snapshot.pane_warning:
        warning_lines.append(f"panes: {snapshot.pane_warning}")
    if len(warning_lines) == 0:
        return None
    return Panel("\n".join(warning_lines), title="Warnings", border_style="yellow")

def build_trace_renderable(
    snapshot: "TraceSnapshot",
    until: "TraceUntil",
    exit_code: int | None,
    attempt: int,
    elapsed_seconds: float,
    next_poll_seconds: float,
    checked_at: str,
) -> "RenderableType":
    from rich.console import Group

    renderables = [
        _build_overview_panel(
            snapshot=snapshot,
            until=until,
            exit_code=exit_code,
            attempt=attempt,
            elapsed_seconds=elapsed_seconds,
            next_poll_seconds=next_poll_seconds,
            checked_at=checked_at,
        ),
        _build_panes_table(snapshot=snapshot),
    ]
    warning_panel = _build_warning_panel(snapshot=snapshot)
    if warning_panel is not None:
        renderables.append(warning_panel)
    return Group(*renderables)
