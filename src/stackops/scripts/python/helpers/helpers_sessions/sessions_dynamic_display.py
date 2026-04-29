from dataclasses import dataclass
from datetime import datetime
from time import monotonic
from typing import Literal, NotRequired, TypeAlias, TypedDict

from rich import box
from rich.console import Group, RenderableType
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn
from rich.table import Table

from stackops.utils.schemas.layouts.layout_types import TabConfig

DynamicSessionBackend: TypeAlias = Literal["zellij", "tmux"]
DynamicRunPhase: TypeAlias = Literal["starting", "monitoring", "completed"]

LIVE_REFRESH_PER_SECOND = 8
RECENT_COMPLETED_LIMIT = 8


class DynamicTabTask(TypedDict):
    index: int
    runtime_tab_name: str
    tab: TabConfig
    started_at_seconds: NotRequired[float]
    completion_duration_seconds: NotRequired[float]


class DynamicStartResult(TypedDict):
    success: bool
    message: NotRequired[str]
    error: NotRequired[str]


@dataclass(frozen=True, slots=True)
class DynamicRunDisplay:
    layout_name: str
    backend: DynamicSessionBackend
    session_name: str | None
    phase: DynamicRunPhase
    max_parallel_tabs: int
    total_count: int
    completed_count: int
    pending_count: int
    active_tasks: tuple[DynamicTabTask, ...]
    recent_completed_tasks: tuple[DynamicTabTask, ...]
    poll_seconds: float
    elapsed_seconds: float
    checked_at_text: str
    message: str


def _checked_at_text() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


def format_duration(seconds: float) -> str:
    rounded_seconds = max(0, int(round(seconds)))
    hours, rem = divmod(rounded_seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def _phase_label(phase: DynamicRunPhase) -> str:
    match phase:
        case "starting":
            return "starting"
        case "monitoring":
            return "monitoring"
        case "completed":
            return "completed"


def _phase_style(phase: DynamicRunPhase) -> str:
    match phase:
        case "starting":
            return "yellow"
        case "monitoring":
            return "cyan"
        case "completed":
            return "green"


def _build_progress(total_count: int, completed_count: int) -> Progress:
    progress = Progress(
        TextColumn("[bold cyan]Tabs"), BarColumn(bar_width=None), MofNCompleteColumn(), TextColumn("{task.percentage:>3.0f}%"), expand=True
    )
    progress.add_task("tabs", total=total_count, completed=completed_count)
    return progress


def _build_overview_table(display: DynamicRunDisplay) -> Table:
    overview = Table.grid(expand=True)
    overview.add_column(style="bold cyan", no_wrap=True)
    overview.add_column(style="white", overflow="fold")
    overview.add_row("Layout", display.layout_name)
    overview.add_row("Backend", display.backend)
    overview.add_row("Session", display.session_name or "starting")
    overview.add_row("Phase", _phase_label(phase=display.phase))
    overview.add_row("Elapsed", format_duration(seconds=display.elapsed_seconds))
    overview.add_row("Checked", display.checked_at_text)
    overview.add_row("Concurrency", str(display.max_parallel_tabs))
    overview.add_row("Poll", f"{display.poll_seconds:0.1f}s")
    overview.add_row("Counts", f"{display.completed_count} completed, {len(display.active_tasks)} active, {display.pending_count} pending")
    overview.add_row("Message", display.message)
    return overview


def _build_active_tasks_table(active_tasks: tuple[DynamicTabTask, ...]) -> Table:
    table = Table(title="Active Monitored Tabs", box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("#", justify="right", style="cyan", no_wrap=True)
    table.add_column("Status", style="cyan", no_wrap=True)
    table.add_column("Runtime Tab", style="white", overflow="fold")
    if len(active_tasks) == 0:
        table.add_row("n/a", "idle", "No active tabs.", style="dim")
        return table
    for task in active_tasks:
        table.add_row(
            str(task["index"] + 1),
            "active",
            task["runtime_tab_name"],
        )
    return table


def _build_recent_completed_table(recent_completed_tasks: tuple[DynamicTabTask, ...]) -> Table:
    table = Table(title="Recently Completed Tabs", box=box.SIMPLE, expand=True)
    table.add_column("#", justify="right", style="green", no_wrap=True)
    table.add_column("Runtime Tab", style="green", overflow="fold")
    table.add_column("Duration", style="cyan", no_wrap=True)
    if len(recent_completed_tasks) == 0:
        table.add_row("n/a", "No completed tabs yet.", "n/a", style="dim")
        return table
    for task in recent_completed_tasks:
        completion_duration_seconds = task.get("completion_duration_seconds")
        duration_text = "n/a" if completion_duration_seconds is None else format_duration(seconds=completion_duration_seconds)
        table.add_row(str(task["index"] + 1), task["runtime_tab_name"], duration_text)
    return table


def build_dashboard(display: DynamicRunDisplay) -> RenderableType:
    progress = _build_progress(total_count=display.total_count, completed_count=display.completed_count)
    overview = _build_overview_table(display=display)
    return Group(
        Panel(Group(progress, overview), title="Dynamic Tab Runner", border_style=_phase_style(phase=display.phase), box=box.DOUBLE),
        _build_active_tasks_table(active_tasks=display.active_tasks),
        _build_recent_completed_table(recent_completed_tasks=display.recent_completed_tasks),
    )


def create_display(
    layout_name: str,
    backend: DynamicSessionBackend,
    session_name: str | None,
    phase: DynamicRunPhase,
    max_parallel_tabs: int,
    total_count: int,
    completed_count: int,
    pending_count: int,
    active_tasks: tuple[DynamicTabTask, ...],
    completed_tasks: list[DynamicTabTask],
    poll_seconds: float,
    started_at: float,
    message: str,
) -> DynamicRunDisplay:
    return DynamicRunDisplay(
        layout_name=layout_name,
        backend=backend,
        session_name=session_name,
        phase=phase,
        max_parallel_tabs=max_parallel_tabs,
        total_count=total_count,
        completed_count=completed_count,
        pending_count=pending_count,
        active_tasks=active_tasks,
        recent_completed_tasks=tuple(completed_tasks[-RECENT_COMPLETED_LIMIT:]),
        poll_seconds=poll_seconds,
        elapsed_seconds=monotonic() - started_at,
        checked_at_text=_checked_at_text(),
        message=message,
    )


def update_dashboard(live: Live, display: DynamicRunDisplay) -> None:
    live.update(build_dashboard(display=display))
