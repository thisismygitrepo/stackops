"""Tmux backend operations for dynamic tab scheduling."""

import os
import shlex
import subprocess

from stackops.cluster.sessions_managers.session_conflict import SessionConflictAction
from stackops.cluster.sessions_managers.tmux.tmux_utils.tmux_common import RUN_ALL_STATE_OPTION
from stackops.cluster.sessions_managers.tmux.tmux_utils.tmux_execution import run_tmux_commands
from stackops.cluster.sessions_managers.tmux.tmux_utils.tmux_layout import build_tmux_new_window_tab_commands
from stackops.scripts.python.helpers.helpers_sessions._attach_common import quote_powershell
from stackops.scripts.python.helpers.helpers_sessions._tmux_backend_processes import find_meaningful_pane_process_label
from stackops.scripts.python.helpers.helpers_sessions.sessions_dynamic_display import DynamicStartResult, DynamicTabTask
from stackops.utils.schemas.layouts.layout_types import LayoutConfig, PaneConfig, TabConfig


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


def _tracked_tab(tab: TabConfig) -> TabConfig:
    panes: list[PaneConfig] = []
    for pane in tab["panes"]:
        if os.name == "nt":
            set_state = f"""tmux set-option -p -t $env:TMUX_PANE '{RUN_ALL_STATE_OPTION}'"""
            command = f"""{set_state} running; try {{ Invoke-Expression {quote_powershell(pane["command"])} }} finally {{ {set_state} finished }}"""
        else:
            set_state = f"""tmux set-option -p -t "$TMUX_PANE" {RUN_ALL_STATE_OPTION}"""
            command = f"""{set_state} running; eval {shlex.quote(pane["command"])}; {set_state} finished"""
        panes.append({**pane, "command": command})
    return {**tab, "panes": panes}


def spawn_tab(session_name: str, task: DynamicTabTask) -> None:
    run_tmux_commands(
        commands=build_tmux_new_window_tab_commands(session_name=session_name, tab=_tracked_tab(task["tab"]), exit_mode="backToShell"),
        timeout_seconds=30,
    )


def close_tab(session_name: str, runtime_tab_name: str) -> None:
    _run_command(args=["kill-window", "-t", f"{session_name}:{runtime_tab_name}"])


def _start_initial_session_raw(session_name: str, initial_tasks: list[DynamicTabTask], on_conflict: SessionConflictAction) -> str:
    if len(initial_tasks) == 0:
        raise ValueError("No initial tasks provided for tmux startup.")
    from stackops.cluster.sessions_managers.tmux.tmux_local import TmuxLayoutGenerator

    initial_layout: LayoutConfig = {"layoutName": session_name, "layoutTabs": [_tracked_tab(task["tab"]) for task in initial_tasks]}
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
            "#{?pane_dead,exited,#{" + RUN_ALL_STATE_OPTION + "}}\t#{pane_pid}",
        ]
    )
    if result.returncode != 0:
        if _target_is_missing(stderr=result.stderr):
            return False
        detail = (result.stderr or result.stdout or "Unknown tmux error").strip()
        raise RuntimeError(f"Failed to inspect tmux tab '{task['runtime_tab_name']}': {detail}")

    for line in result.stdout.splitlines():
        state, _, pane_pid = line.partition("\t")
        if state == "exited":
            continue
        # A command can return to its shell while a background job still uses the pane.
        if state != "finished" or find_meaningful_pane_process_label(pane_pid) is not None:
            return True
    return False
