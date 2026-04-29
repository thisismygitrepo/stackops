"""Tmux backend operations for dynamic tab scheduling."""

import subprocess

from stackops.cluster.sessions_managers.session_conflict import SessionConflictAction
from stackops.scripts.python.helpers.helpers_sessions._tmux_backend_processes import classify_pane_status, find_meaningful_pane_process_label
from stackops.scripts.python.helpers.helpers_sessions.sessions_dynamic_display import DynamicStartResult, DynamicTabTask
from stackops.utils.schemas.layouts.layout_types import LayoutConfig


def _run_command(args: list[str]) -> None:
    cmd = ["tmux", *args]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
    if result.returncode != 0:
        stderr = result.stderr.strip()
        stdout = result.stdout.strip()
        detail = stderr if stderr != "" else stdout
        raise RuntimeError(f"Failed command: {' '.join(cmd)}\n{detail}")


def _run_capture(args: list[str]) -> subprocess.CompletedProcess[str]:
    cmd = ["tmux", *args]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)


def spawn_tab(session_name: str, task: DynamicTabTask) -> None:
    tab = task["tab"]
    runtime_tab_name = task["runtime_tab_name"]
    _run_command(args=["new-window", "-t", f"{session_name}:", "-n", runtime_tab_name, "-c", tab["startDir"]])
    _run_command(args=["send-keys", "-t", f"{session_name}:{runtime_tab_name}", tab["command"], "C-m"])


def close_tab(session_name: str, runtime_tab_name: str) -> None:
    _run_command(args=["kill-window", "-t", f"{session_name}:{runtime_tab_name}"])


def _start_initial_session_raw(session_name: str, initial_tasks: list[DynamicTabTask], on_conflict: SessionConflictAction) -> str:
    if len(initial_tasks) == 0:
        raise ValueError("No initial tasks provided for tmux startup.")
    from stackops.cluster.sessions_managers.tmux.tmux_local import TmuxLayoutGenerator

    initial_layout: LayoutConfig = {"layoutName": session_name, "layoutTabs": [task["tab"] for task in initial_tasks]}
    generator = TmuxLayoutGenerator(layout_config=initial_layout, session_name=session_name, exit_mode="backToShell")
    generator.create_layout_file()
    generator.run(on_conflict=on_conflict)
    return generator.session_name


def start_initial_session(
    layout_name: str, initial_tasks: list[DynamicTabTask], on_conflict: SessionConflictAction
) -> tuple[list[str], dict[str, DynamicStartResult]]:
    session_name = layout_name.replace(" ", "_")
    try:
        actual_session_name = _start_initial_session_raw(session_name=session_name, initial_tasks=initial_tasks, on_conflict=on_conflict)
    except Exception as exc:
        return [], {session_name: {"success": False, "error": str(exc)}}
    return [actual_session_name], {actual_session_name: {"success": True, "message": "tmux dynamic session started"}}


def _parse_pane_line(line: str) -> dict[str, str]:
    parts = line.split("\t")
    if len(parts) != 5:
        raise RuntimeError(f"Unexpected tmux pane status line: {line}")
    return {"pane_index": parts[0], "pane_command": parts[1], "pane_dead": parts[2], "pane_dead_status": parts[3], "pane_pid": parts[4]}


def _target_is_missing(stderr: str) -> bool:
    error_text = stderr.strip().lower()
    return "can't find session" in error_text or "can't find window" in error_text or "no server running" in error_text


def is_task_running(session_name: str, task: DynamicTabTask) -> bool:
    result = _run_capture(
        args=[
            "list-panes",
            "-t",
            f"{session_name}:{task['runtime_tab_name']}",
            "-F",
            "#{pane_index}\t#{pane_current_command}\t#{?pane_dead,dead,}\t#{pane_dead_status}\t#{pane_pid}",
        ]
    )
    if result.returncode != 0:
        if _target_is_missing(stderr=result.stderr):
            return False
        detail = (result.stderr or result.stdout or "Unknown tmux error").strip()
        raise RuntimeError(f"Failed to inspect tmux tab '{task['runtime_tab_name']}': {detail}")

    pane_lines = [line for line in result.stdout.splitlines() if line.strip()]
    if len(pane_lines) == 0:
        return False

    for line in pane_lines:
        pane = _parse_pane_line(line=line)
        _, status_text = classify_pane_status(pane, pane_process_label_finder=find_meaningful_pane_process_label)
        if status_text.startswith("running:"):
            return True
    return False
