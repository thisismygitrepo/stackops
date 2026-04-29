"""Dynamic tab scheduling for a single layout."""

from collections import deque
from pathlib import Path
import subprocess
import tempfile
import time
from time import monotonic
from typing import Literal

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from stackops.cluster.sessions_managers.session_conflict import SessionConflictAction
from stackops.cluster.sessions_managers.zellij.zellij_utils.zellij_local_helper import parse_command, format_args_for_kdl
from stackops.cluster.sessions_managers.zellij.zellij_utils.zellij_local_helper import check_command_status
from stackops.cluster.sessions_managers.zellij.zellij_local_manager import ZellijLocalManager
from stackops.cluster.sessions_managers.zellij.zellij_utils.monitoring_types import StartResult
from stackops.scripts.python.helpers.helpers_sessions.sessions_dynamic_display import (
    LIVE_REFRESH_PER_SECOND,
    DynamicRunPhase,
    DynamicTabTask,
    build_dashboard,
    create_display,
    format_duration,
    update_dashboard,
)
from stackops.utils.schemas.layouts.layout_types import LayoutConfig, TabConfig


def _build_runtime_tab_name(original_tab_name: str, index: int) -> str:
    return f"{original_tab_name}__dynamic_{index + 1}"


def _run_zellij_action(session_name: str, args: list[str]) -> None:
    cmd = ["zellij", "--session", session_name, *args]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
    if result.returncode != 0:
        stderr = result.stderr.strip()
        stdout = result.stdout.strip()
        detail = stderr if stderr != "" else stdout
        raise RuntimeError(f"Failed command: {' '.join(cmd)}\n{detail}")


def _create_single_tab_layout_file(task: DynamicTabTask) -> str:
    tab = task["tab"]
    tab_name = task["runtime_tab_name"].replace('"', '\\"')
    tab_cwd = tab["startDir"].replace('"', '\\"')
    command_text = tab["command"]
    _, _args = parse_command(command_text)
    args_for_bash = ["-lc", command_text]
    args_kdl = format_args_for_kdl(args_for_bash)
    layout_content = f"""layout {{
  tab name="{tab_name}" cwd="{tab_cwd}" {{
    pane command="/bin/bash" {{
      args {args_kdl}
    }}
  }}
}}
"""
    layout_dir = Path.home().joinpath("tmp_results/sessions/zellij_layouts_dynamic")
    layout_dir.mkdir(parents=True, exist_ok=True)
    layout_file_path = tempfile.mkstemp(suffix="_dynamic_tab.kdl", dir=layout_dir)[1]
    Path(layout_file_path).write_text(layout_content, encoding="utf-8")
    return layout_file_path


def _spawn_tab(session_name: str, task: DynamicTabTask) -> None:
    runtime_tab_name = task["runtime_tab_name"]
    layout_file = _create_single_tab_layout_file(task=task)
    _run_zellij_action(session_name=session_name, args=["action", "new-tab", "--name", runtime_tab_name, "--layout", layout_file])


def _close_tab(session_name: str, runtime_tab_name: str) -> None:
    try:
        go_to_cmd = ["zellij", "--session", session_name, "action", "go-to-tab-name", runtime_tab_name]
        go_to_result = subprocess.run(go_to_cmd, capture_output=True, text=True, timeout=2.0, check=False)
        if go_to_result.returncode != 0:
            return
        time.sleep(0.1)
        close_cmd = ["zellij", "--session", session_name, "action", "close-tab"]
        subprocess.run(close_cmd, capture_output=True, text=True, timeout=2.0, check=False)
    except Exception:
        return


def _run_tmux_command(args: list[str]) -> None:
    cmd = ["tmux", *args]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
    if result.returncode != 0:
        stderr = result.stderr.strip()
        stdout = result.stdout.strip()
        detail = stderr if stderr != "" else stdout
        raise RuntimeError(f"Failed command: {' '.join(cmd)}\n{detail}")


def _spawn_tab_tmux(session_name: str, task: DynamicTabTask) -> None:
    tab = task["tab"]
    runtime_tab_name = task["runtime_tab_name"]
    _run_tmux_command(args=["new-window", "-t", f"{session_name}:", "-n", runtime_tab_name, "-c", tab["startDir"]])
    _run_tmux_command(args=["send-keys", "-t", f"{session_name}:{runtime_tab_name}", tab["command"], "C-m"])


def _close_tab_tmux(session_name: str, runtime_tab_name: str) -> None:
    _run_tmux_command(args=["kill-window", "-t", f"{session_name}:{runtime_tab_name}"])


def _start_tmux_initial_session(session_name: str, initial_tasks: list[DynamicTabTask], on_conflict: SessionConflictAction) -> str:
    if len(initial_tasks) == 0:
        raise ValueError("No initial tasks provided for tmux startup.")
    from stackops.cluster.sessions_managers.tmux.tmux_local import TmuxLayoutGenerator

    initial_layout: LayoutConfig = {"layoutName": session_name, "layoutTabs": [task["tab"] for task in initial_tasks]}
    generator = TmuxLayoutGenerator(layout_config=initial_layout, session_name=session_name, exit_mode="backToShell")
    generator.create_layout_file()
    generator.run(on_conflict=on_conflict)
    return generator.session_name


def _is_task_running(task: DynamicTabTask) -> bool:
    tab = task["tab"]
    tab_for_check: TabConfig = {"tabName": task["runtime_tab_name"], "startDir": tab["startDir"], "command": tab["command"]}
    layout_for_check: LayoutConfig = {"layoutName": "dynamic-check", "layoutTabs": [tab_for_check]}
    status = check_command_status(tab_name=task["runtime_tab_name"], layout_config=layout_for_check)
    return status.get("running", False)


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
        if backend_resolved == "zellij":
            manager_zellij = ZellijLocalManager(session_layouts=[initial_layout])
            start_results = manager_zellij.start_all_sessions(on_conflict=on_conflict, poll_interval=1.0, poll_seconds=12.0)
            session_names = manager_zellij.get_all_session_names()
        else:
            session_name_for_tmux = layout["layoutName"].replace(" ", "_")
            try:
                actual_session_name = _start_tmux_initial_session(
                    session_name=session_name_for_tmux, initial_tasks=initial_tasks, on_conflict=on_conflict
                )
                start_results: dict[str, StartResult] = {actual_session_name: {"success": True, "message": "tmux dynamic session started"}}
            except Exception as exc:
                start_results = {session_name_for_tmux: {"success": False, "error": str(exc)}}
            else:
                session_names = [actual_session_name]

        failures = {name: result for name, result in start_results.items() if not result.get("success", False)}
        if len(failures) > 0:
            details = "; ".join(f"{name}: {result.get('error', 'unknown error')}" for name, result in failures.items())
            raise ValueError(f"Failed to start dynamic session: {details}")

        if len(session_names) != 1:
            raise ValueError("Expected exactly one session for dynamic tab runner.")
        session_name = session_names[0]

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

        while len(active_tasks) > 0:
            finished_names: list[str] = []
            for runtime_tab_name, task in list(active_tasks.items()):
                if not _is_task_running(task=task):
                    finished_names.append(runtime_tab_name)

            started_count = 0
            for runtime_tab_name in finished_names:
                finished_task = active_tasks.pop(runtime_tab_name)
                completed_tasks.append(finished_task)
                completed_count += 1
                if kill_finished_tabs:
                    if backend_resolved == "zellij":
                        _close_tab(session_name=session_name, runtime_tab_name=runtime_tab_name)
                    else:
                        _close_tab_tmux(session_name=session_name, runtime_tab_name=runtime_tab_name)

                if len(pending_tasks) > 0:
                    next_task = pending_tasks.popleft()
                    if backend_resolved == "zellij":
                        _spawn_tab(session_name=session_name, task=next_task)
                    else:
                        _spawn_tab_tmux(session_name=session_name, task=next_task)
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
