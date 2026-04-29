"""Dynamic tab scheduling for a single layout."""

from collections import deque
import time
from time import monotonic
from typing import Literal

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from stackops.cluster.sessions_managers.session_conflict import SessionConflictAction
from stackops.scripts.python.helpers.helpers_sessions import sessions_dynamic_tmux, sessions_dynamic_zellij
from stackops.scripts.python.helpers.helpers_sessions.sessions_dynamic_display import (
    LIVE_REFRESH_PER_SECOND,
    DynamicRunPhase,
    DynamicSessionBackend,
    DynamicStartResult,
    DynamicTabTask,
    build_dashboard,
    create_display,
    format_duration,
    update_dashboard,
)
from stackops.utils.schemas.layouts.layout_types import LayoutConfig, TabConfig

INITIAL_COMPLETION_POLL_DELAY_SECONDS = 2.0


def _build_runtime_tab_name(original_tab_name: str, index: int) -> str:
    return f"{original_tab_name}__dynamic_{index + 1}"


def _start_backend_session(
    backend: DynamicSessionBackend,
    layout_name: str,
    initial_layout: LayoutConfig,
    initial_tasks: list[DynamicTabTask],
    on_conflict: SessionConflictAction,
) -> tuple[list[str], dict[str, DynamicStartResult]]:
    match backend:
        case "zellij":
            return sessions_dynamic_zellij.start_initial_session(layout=initial_layout, on_conflict=on_conflict)
        case "tmux":
            return sessions_dynamic_tmux.start_initial_session(layout_name=layout_name, initial_tasks=initial_tasks, on_conflict=on_conflict)


def _spawn_backend_tab(backend: DynamicSessionBackend, session_name: str, task: DynamicTabTask) -> None:
    match backend:
        case "zellij":
            sessions_dynamic_zellij.spawn_tab(session_name=session_name, task=task)
        case "tmux":
            sessions_dynamic_tmux.spawn_tab(session_name=session_name, task=task)


def _close_backend_tab(backend: DynamicSessionBackend, session_name: str, runtime_tab_name: str) -> None:
    match backend:
        case "zellij":
            sessions_dynamic_zellij.close_tab(session_name=session_name, runtime_tab_name=runtime_tab_name)
        case "tmux":
            sessions_dynamic_tmux.close_tab(session_name=session_name, runtime_tab_name=runtime_tab_name)


def _is_dynamic_task_running(backend: DynamicSessionBackend, session_name: str, task: DynamicTabTask) -> bool:
    match backend:
        case "zellij":
            return sessions_dynamic_zellij.is_task_running(task=task)
        case "tmux":
            return sessions_dynamic_tmux.is_task_running(session_name=session_name, task=task)


def _validate_backend(backend: Literal["zellij", "z", "tmux", "t", "auto", "a"]) -> Literal["zellij", "tmux"]:
    import platform

    backend_lower = backend.lower()
    if backend_lower in {"zellij", "z"}:
        if platform.system().lower() == "windows":
            raise ValueError("Dynamic tab runner requires zellij and is not supported on Windows.")
        return "zellij"
    if backend_lower in {"tmux", "t"}:
        if platform.system().lower() == "windows":
            raise ValueError("Dynamic tab runner requires tmux and is not supported on Windows.")
        return "tmux"
    if backend_lower in {"auto", "a"}:
        if platform.system().lower() == "windows":
            raise ValueError("Dynamic tab runner requires zellij or tmux and is not supported on Windows.")
        return "zellij"
    raise ValueError(f"Unsupported backend for dynamic tabs: {backend}")


def run_dynamic(
    layout: LayoutConfig,
    max_parallel_tabs: int,
    kill_finished_tabs: bool,
    backend: Literal["zellij", "z", "tmux", "t", "auto", "a"],
    on_conflict: SessionConflictAction,
    poll_seconds: float,
) -> None:
    backend_resolved = _validate_backend(backend=backend)
    if max_parallel_tabs <= 0:
        raise ValueError("max_parallel_tabs must be a positive integer.")
    if poll_seconds <= 0:
        raise ValueError("poll_seconds must be a positive number.")
    if len(layout["layoutTabs"]) == 0:
        raise ValueError("Selected layout has no tabs.")

    all_tasks: list[DynamicTabTask] = []
    for index, tab in enumerate(layout["layoutTabs"]):
        runtime_tab_name = _build_runtime_tab_name(original_tab_name=tab["tabName"], index=index)
        runtime_tab: TabConfig = {"tabName": runtime_tab_name, "startDir": tab["startDir"], "command": tab["command"]}
        all_tasks.append({"index": index, "runtime_tab_name": runtime_tab_name, "tab": runtime_tab})

    first_count = min(max_parallel_tabs, len(all_tasks))
    initial_tasks = all_tasks[:first_count]
    pending_tasks: deque[DynamicTabTask] = deque(all_tasks[first_count:])
    initial_layout: LayoutConfig = {"layoutName": layout["layoutName"], "layoutTabs": [task["tab"] for task in initial_tasks]}
    session_names: list[str] = []
    total_count = len(all_tasks)
    completed_tasks: list[DynamicTabTask] = []
    started_at = monotonic()
    console = Console()

    with Live(
        build_dashboard(
            display=create_display(
                layout_name=layout["layoutName"],
                backend=backend_resolved,
                session_name=None,
                phase="starting",
                max_parallel_tabs=max_parallel_tabs,
                total_count=total_count,
                completed_count=0,
                pending_count=len(pending_tasks),
                active_tasks=tuple(initial_tasks),
                completed_tasks=completed_tasks,
                poll_seconds=poll_seconds,
                started_at=started_at,
                message="Starting initial tab batch.",
            )
        ),
        console=console,
        refresh_per_second=LIVE_REFRESH_PER_SECOND,
        transient=False,
    ) as live:
        session_names, start_results = _start_backend_session(
            backend=backend_resolved,
            layout_name=layout["layoutName"],
            initial_layout=initial_layout,
            initial_tasks=initial_tasks,
            on_conflict=on_conflict,
        )

        failures = {name: result for name, result in start_results.items() if not result.get("success", False)}
        if len(failures) > 0:
            details = "; ".join(f"{name}: {result.get('error', 'unknown error')}" for name, result in failures.items())
            raise ValueError(f"Failed to start dynamic session: {details}")

        if len(session_names) != 1:
            raise ValueError("Expected exactly one session for dynamic tab runner.")
        session_name = session_names[0]
        initial_started_at = monotonic()
        for task in initial_tasks:
            task["started_at_seconds"] = initial_started_at

        active_tasks: dict[str, DynamicTabTask] = {task["runtime_tab_name"]: task for task in initial_tasks}
        completed_count = 0
        update_dashboard(
            live=live,
            display=create_display(
                layout_name=layout["layoutName"],
                backend=backend_resolved,
                session_name=session_name,
                phase="monitoring",
                max_parallel_tabs=max_parallel_tabs,
                total_count=total_count,
                completed_count=completed_count,
                pending_count=len(pending_tasks),
                active_tasks=tuple(active_tasks.values()),
                completed_tasks=completed_tasks,
                poll_seconds=poll_seconds,
                started_at=started_at,
                message="Monitoring active tabs.",
            ),
        )
        if len(active_tasks) > 0:
            update_dashboard(
                live=live,
                display=create_display(
                    layout_name=layout["layoutName"],
                    backend=backend_resolved,
                    session_name=session_name,
                    phase="monitoring",
                    max_parallel_tabs=max_parallel_tabs,
                    total_count=total_count,
                    completed_count=completed_count,
                    pending_count=len(pending_tasks),
                    active_tasks=tuple(active_tasks.values()),
                    completed_tasks=completed_tasks,
                    poll_seconds=poll_seconds,
                    started_at=started_at,
                    message=f"Waiting {INITIAL_COMPLETION_POLL_DELAY_SECONDS:0.1f}s before the first completion check.",
                ),
            )
            time.sleep(INITIAL_COMPLETION_POLL_DELAY_SECONDS)

        while len(active_tasks) > 0:
            checked_at = monotonic()
            finished_names: list[str] = []
            for runtime_tab_name, task in list(active_tasks.items()):
                if not _is_dynamic_task_running(backend=backend_resolved, session_name=session_name, task=task):
                    finished_names.append(runtime_tab_name)

            started_count = 0
            for runtime_tab_name in finished_names:
                finished_task = active_tasks.pop(runtime_tab_name)
                task_started_at = finished_task.get("started_at_seconds")
                if task_started_at is not None:
                    finished_task["completion_duration_seconds"] = max(0.0, checked_at - task_started_at)
                completed_tasks.append(finished_task)
                completed_count += 1
                if kill_finished_tabs:
                    _close_backend_tab(backend=backend_resolved, session_name=session_name, runtime_tab_name=runtime_tab_name)

                if len(pending_tasks) > 0:
                    next_task = pending_tasks.popleft()
                    _spawn_backend_tab(backend=backend_resolved, session_name=session_name, task=next_task)
                    next_task["started_at_seconds"] = monotonic()
                    active_tasks[next_task["runtime_tab_name"]] = next_task
                    started_count += 1

            if len(finished_names) > 0:
                message = f"Finished {len(finished_names)} tab(s); started {started_count} replacement tab(s)."
            else:
                message = "No tabs finished in the last poll."
            phase: DynamicRunPhase = "completed" if len(active_tasks) == 0 else "monitoring"
            update_dashboard(
                live=live,
                display=create_display(
                    layout_name=layout["layoutName"],
                    backend=backend_resolved,
                    session_name=session_name,
                    phase=phase,
                    max_parallel_tabs=max_parallel_tabs,
                    total_count=total_count,
                    completed_count=completed_count,
                    pending_count=len(pending_tasks),
                    active_tasks=tuple(active_tasks.values()),
                    completed_tasks=completed_tasks,
                    poll_seconds=poll_seconds,
                    started_at=started_at,
                    message=message,
                ),
            )

            if len(active_tasks) > 0:
                time.sleep(poll_seconds)

    console.print(
        Panel(
            f"Completed {total_count} tabs for `{layout['layoutName']}` in {format_duration(seconds=monotonic() - started_at)}.",
            title="Complete",
            border_style="green",
        )
    )
