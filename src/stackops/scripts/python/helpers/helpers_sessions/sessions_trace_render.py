from pathlib import Path
from typing import TYPE_CHECKING

from stackops.scripts.python.helpers.helpers_sessions.sessions_trace_layout import (
    measure_lines,
    plan_trace_layout,
)

PROGRESS_BAR_WIDTH = 16
WARNINGS_LIMIT = 3
_PENDING_CATEGORY_LABELS: tuple[tuple[str, str], ...] = (
    ("running", "running"),
    ("exited", "exited"),
    ("unknown", "unknown"),
    ("idle-shell", "idle"),
)

if TYPE_CHECKING:
    from rich.console import Console, RenderableType
    from rich.panel import Panel
    from rich.table import Table
    from stackops.scripts.python.helpers.helpers_sessions.session_trace_models import (
        TraceBackend,
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


def _estimate_remaining_seconds(matched_targets: int, total_targets: int, elapsed_seconds: float) -> float | None:
    if total_targets <= 0 or matched_targets <= 0 or matched_targets >= total_targets:
        return None
    completion_ratio = matched_targets / total_targets
    return elapsed_seconds * ((1.0 - completion_ratio) / completion_ratio)


def _render_progress_bar(matched_targets: int, total_targets: int, bar_style: str) -> str:
    if total_targets <= 0:
        return f"[dim]{'·' * PROGRESS_BAR_WIDTH} waiting for targets[/dim]"
    filled = (
        PROGRESS_BAR_WIDTH
        if matched_targets >= total_targets
        else min(PROGRESS_BAR_WIDTH, max(1, round((matched_targets / total_targets) * PROGRESS_BAR_WIDTH)))
    )
    percentage = (matched_targets / total_targets) * 100.0
    return (
        f"[{bar_style}]{'█' * filled}[/{bar_style}]"
        f"[dim]{'·' * (PROGRESS_BAR_WIDTH - filled)}[/dim]"
        f" {matched_targets}/{total_targets} ({percentage:.0f}%)"
    )


def _session_state(snapshot: "TraceSnapshot") -> tuple[str, str]:
    if snapshot.criterion_satisfied:
        return ("done", "green")
    if snapshot.session_exists:
        return ("active", "cyan")
    return ("missing", "yellow")


def _pending_panes(snapshot: "TraceSnapshot") -> tuple["TracePaneState", ...]:
    return tuple(pane for pane in snapshot.panes if not pane.matched)


def _settled_panes(snapshot: "TraceSnapshot") -> tuple["TracePaneState", ...]:
    return tuple(pane for pane in snapshot.panes if pane.matched)


def _pending_summary(pending_panes: tuple["TracePaneState", ...]) -> str:
    if len(pending_panes) == 0:
        return "—"
    category_counts: dict[str, int] = {}
    for pane in pending_panes:
        category_counts[pane.category] = category_counts.get(pane.category, 0) + 1
    parts = [
        f"{category_counts[category]} {label}"
        for category, label in _PENDING_CATEGORY_LABELS
        if category_counts.get(category, 0) > 0
    ]
    return ", ".join(parts)


def _pane_row_style(pane: "TracePaneState") -> str:
    match pane.category:
        case "running":
            return "red"
        case "unknown":
            return "yellow"
        case "exited":
            return "magenta"
        case "idle-shell":
            return "cyan"


def _shorten_dir(cwd: str, home: str) -> str:
    if cwd == home:
        return "~"
    if cwd.startswith(home + "/"):
        return "~" + cwd[len(home):]
    return cwd


def _build_header_panel(
    snapshots: tuple["TraceSnapshot", ...],
    backend: "TraceBackend",
    until: "TraceUntil",
    exit_code: int | None,
    attempt: int,
    elapsed_seconds: float,
    next_poll_seconds: float,
    checked_at: str,
) -> "Panel":
    from rich import box
    from rich.panel import Panel

    total_targets = sum(snapshot.total_targets for snapshot in snapshots)
    matched_targets = sum(snapshot.matched_targets for snapshot in snapshots)
    total_panes = sum(len(snapshot.panes) for snapshot in snapshots)
    all_satisfied = all(snapshot.criterion_satisfied for snapshot in snapshots)
    session_word = "session" if len(snapshots) == 1 else "sessions"
    pane_word = "pane" if total_panes == 1 else "panes"
    eta_seconds = _estimate_remaining_seconds(
        matched_targets=matched_targets,
        total_targets=total_targets,
        elapsed_seconds=elapsed_seconds,
    )
    eta_text = "done" if all_satisfied else format_duration(eta_seconds)
    next_poll_text = "done" if all_satisfied else f"{next_poll_seconds:0.1f}s"
    header_lines = [
        f"until [bold cyan]{criterion_label(until=until, exit_code=exit_code)}[/bold cyan]"
        f" · [white]{len(snapshots)} {session_word}[/white]"
        f" · [white]{total_panes} {pane_word}[/white]",
        f"{_render_progress_bar(matched_targets=matched_targets, total_targets=total_targets, bar_style='green' if all_satisfied else 'cyan')}"
        f" · ETA [bold]{eta_text}[/bold]",
        f"elapsed [bold]{format_duration(elapsed_seconds)}[/bold]"
        f" · check [bold]#{attempt}[/bold]"
        f" · next poll [bold]{next_poll_text}[/bold]"
        f" · checked {checked_at}",
    ]
    return Panel(
        "\n".join(header_lines),
        title=f"Sessions Trace · {backend}",
        border_style="green" if all_satisfied else "cyan",
        box=box.DOUBLE,
    )


def _build_sessions_table(snapshots: tuple["TraceSnapshot", ...], attempt: int, sessions_visible: int | None) -> "Table":
    from rich import box
    from rich.markup import escape
    from rich.table import Table

    sessions_table = Table(box=box.SIMPLE, expand=True, show_edge=False, pad_edge=False)
    sessions_table.add_column("Session", style="bold", no_wrap=True, overflow="ellipsis")
    sessions_table.add_column("State", no_wrap=True)
    sessions_table.add_column("Progress", no_wrap=True, ratio=1)
    sessions_table.add_column("Pending", no_wrap=True)
    sessions_table.add_column("Layout", style="dim", no_wrap=True)
    shown_snapshots = snapshots if sessions_visible is None else snapshots[:sessions_visible]
    for snapshot in shown_snapshots:
        state_label, state_style = _session_state(snapshot=snapshot)
        if attempt == 0 and state_label == "missing":
            state_label, state_style = "waiting", "dim"
        sessions_table.add_row(
            escape(snapshot.session_name),
            f"[{state_style}]{state_label}[/{state_style}]",
            _render_progress_bar(
                matched_targets=snapshot.matched_targets,
                total_targets=snapshot.total_targets,
                bar_style="green" if snapshot.criterion_satisfied else "cyan",
            ),
            _pending_summary(pending_panes=_pending_panes(snapshot=snapshot)),
            f"{snapshot.total_windows} win · {len(snapshot.panes)} panes",
            style="green" if snapshot.criterion_satisfied else None,
        )
    hidden_snapshots = snapshots[len(shown_snapshots):]
    if len(hidden_snapshots) > 0:
        done_hidden = sum(1 for snapshot in hidden_snapshots if snapshot.criterion_satisfied)
        sessions_table.add_row(
            escape(f"… and {len(hidden_snapshots)} more sessions ({done_hidden} done)"),
            "",
            "",
            "",
            "",
            style="dim",
        )
    return sessions_table


def _build_panes_table(
    snapshots: tuple["TraceSnapshot", ...],
    attempt: int,
    pending_visible: int | None,
    settled_visible: int | None,
) -> "Table":
    from rich import box
    from rich.markup import escape
    from rich.table import Table

    multiple_sessions = len(snapshots) > 1
    home = str(Path.home())
    panes_table = Table(box=box.SIMPLE, expand=True, show_edge=False, pad_edge=False)
    if multiple_sessions:
        panes_table.add_column("Session", style="bold", no_wrap=True, overflow="ellipsis")
    panes_table.add_column("Win", no_wrap=True, overflow="ellipsis", max_width=24)
    panes_table.add_column("Pane", justify="right", no_wrap=True, overflow="ellipsis", max_width=18)
    summary_column_index = len(panes_table.columns)
    panes_table.add_column("Process", no_wrap=True, overflow="ellipsis", ratio=2)
    panes_table.add_column("Status", no_wrap=True, overflow="ellipsis", ratio=2)
    panes_table.add_column("Dir", style="dim", no_wrap=True, overflow="ellipsis", max_width=26)

    def add_dim_row(text: str) -> None:
        cells: list[str] = ["" for _ in range(len(panes_table.columns))]
        cells[summary_column_index] = escape(text)
        panes_table.add_row(*cells, style="dim")

    def add_pane_row(session_name: str, pane: "TracePaneState", row_style: str) -> None:
        cells: list[str] = []
        if multiple_sessions:
            cells.append(escape(session_name))
        cells.extend(
            (
                escape(f"{pane.window_index}:{pane.window_name}"),
                escape(("●" if pane.is_active else "") + pane.pane_index),
                escape(pane.process_name),
                escape(pane.status_text),
                escape(_shorten_dir(cwd=pane.cwd, home=home)),
            )
        )
        panes_table.add_row(*cells, style=row_style)

    if attempt == 0:
        add_dim_row("waiting for first check…")
        return panes_table

    pending_rows = [
        (snapshot.session_name, pane)
        for snapshot in snapshots
        for pane in _pending_panes(snapshot=snapshot)
    ]
    settled_rows = [
        (snapshot.session_name, pane)
        for snapshot in snapshots
        for pane in _settled_panes(snapshot=snapshot)
    ]
    shown_pending = pending_rows if pending_visible is None else pending_rows[:pending_visible]
    for session_name, pane in shown_pending:
        add_pane_row(session_name=session_name, pane=pane, row_style=_pane_row_style(pane=pane))
    hidden_pending = pending_rows[len(shown_pending):]
    if len(hidden_pending) > 0:
        hidden_summary = _pending_summary(pending_panes=tuple(pane for _, pane in hidden_pending))
        add_dim_row(f"… and {len(hidden_pending)} more pending panes ({hidden_summary})")
    shown_settled = settled_rows if settled_visible is None else settled_rows[:settled_visible]
    for session_name, pane in shown_settled:
        add_pane_row(session_name=session_name, pane=pane, row_style="dim")
    if panes_table.row_count == 0:
        add_dim_row("no observable panes")
    return panes_table


def _build_warning_panel(snapshots: tuple["TraceSnapshot", ...]) -> "Panel | None":
    from rich import box
    from rich.markup import escape
    from rich.panel import Panel

    warning_lines: list[str] = []
    for snapshot in snapshots:
        if snapshot.session_error is not None:
            warning_lines.append(escape(f"{snapshot.session_name}: {snapshot.session_error}"))
        if snapshot.pane_warning is not None:
            warning_lines.append(escape(f"{snapshot.session_name}: {snapshot.pane_warning}"))
    if len(warning_lines) == 0:
        return None
    shown_warnings = warning_lines[:WARNINGS_LIMIT]
    if len(warning_lines) > WARNINGS_LIMIT:
        shown_warnings.append(f"… and {len(warning_lines) - WARNINGS_LIMIT} more warnings")
    return Panel("\n".join(shown_warnings), title="Warnings", border_style="yellow", box=box.SIMPLE)


def build_traces_renderable(
    snapshots: tuple["TraceSnapshot", ...],
    backend: "TraceBackend",
    until: "TraceUntil",
    exit_code: int | None,
    attempt: int,
    elapsed_seconds: float,
    next_poll_seconds: float,
    checked_at: str,
    console: "Console",
) -> "RenderableType":
    from rich.console import Group
    from rich.text import Text

    header = _build_header_panel(
        snapshots=snapshots,
        backend=backend,
        until=until,
        exit_code=exit_code,
        attempt=attempt,
        elapsed_seconds=elapsed_seconds,
        next_poll_seconds=next_poll_seconds,
        checked_at=checked_at,
    )
    warnings = _build_warning_panel(snapshots=snapshots)
    header_height = measure_lines(console=console, renderable=header)
    warnings_height = 0 if warnings is None else measure_lines(console=console, renderable=warnings)

    pending_count = 0
    settled_count = 0
    if attempt > 0:
        pending_count = sum(len(_pending_panes(snapshot=snapshot)) for snapshot in snapshots)
        settled_count = sum(len(_settled_panes(snapshot=snapshot)) for snapshot in snapshots)
    placeholder_rows = 1 if pending_count + settled_count == 0 else 0

    sessions_full = _build_sessions_table(snapshots=snapshots, attempt=attempt, sessions_visible=None)
    panes_full = _build_panes_table(snapshots=snapshots, attempt=attempt, pending_visible=None, settled_visible=None)
    sessions_chrome = measure_lines(console=console, renderable=sessions_full) - sessions_full.row_count
    panes_chrome = measure_lines(console=console, renderable=panes_full) - panes_full.row_count

    layout = plan_trace_layout(
        console_height=console.size.height,
        header_height=header_height,
        warnings_height=warnings_height,
        sessions_chrome=sessions_chrome,
        panes_chrome=panes_chrome,
        session_count=len(snapshots),
        pending_count=pending_count,
        settled_count=settled_count,
        placeholder_rows=placeholder_rows,
    )

    if layout.sessions_visible is None and layout.pending_visible is None:
        sessions_table: Table = sessions_full
        panes_table: Table = panes_full
    else:
        sessions_table = _build_sessions_table(
            snapshots=snapshots,
            attempt=attempt,
            sessions_visible=layout.sessions_visible,
        )
        panes_table = _build_panes_table(
            snapshots=snapshots,
            attempt=attempt,
            pending_visible=layout.pending_visible,
            settled_visible=layout.settled_visible,
        )

    renderables: list[RenderableType] = [header, sessions_table]
    if layout.show_panes:
        renderables.append(panes_table)
    if warnings is not None:
        renderables.append(warnings)
    if len(layout.footer_parts) > 0:
        renderables.append(Text(" · ".join(layout.footer_parts), style="dim"))
    return Group(*renderables)
