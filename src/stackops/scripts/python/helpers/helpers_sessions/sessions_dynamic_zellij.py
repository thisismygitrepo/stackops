"""Zellij backend operations for dynamic tab scheduling."""

import os
from pathlib import Path
import subprocess
import tempfile
import time
from typing import cast

from stackops.cluster.sessions_managers.session_conflict import SessionConflictAction
from stackops.cluster.sessions_managers.zellij.zellij_local_manager import ZellijLocalManager
from stackops.cluster.sessions_managers.zellij.zellij_utils.zellij_local_helper import check_command_status, format_args_for_kdl
from stackops.scripts.python.helpers.helpers_sessions.sessions_dynamic_display import DynamicStartResult, DynamicTabTask
from stackops.utils.schemas.layouts.layout_types import LayoutConfig, TabConfig


def start_initial_session(layout: LayoutConfig, on_conflict: SessionConflictAction) -> tuple[list[str], dict[str, DynamicStartResult]]:
    manager = ZellijLocalManager(session_layouts=[layout])
    start_results = manager.start_all_sessions(on_conflict=on_conflict, poll_interval=1.0, poll_seconds=12.0)
    return manager.get_all_session_names(), cast(dict[str, DynamicStartResult], start_results)


def _run_action(session_name: str, args: list[str]) -> None:
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
    args_kdl = format_args_for_kdl(["-lc", command_text])
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
    file_descriptor, layout_file_path = tempfile.mkstemp(suffix="_dynamic_tab.kdl", dir=layout_dir)
    os.close(file_descriptor)
    Path(layout_file_path).write_text(layout_content, encoding="utf-8")
    return layout_file_path


def spawn_tab(session_name: str, task: DynamicTabTask) -> None:
    runtime_tab_name = task["runtime_tab_name"]
    layout_file = _create_single_tab_layout_file(task=task)
    _run_action(session_name=session_name, args=["action", "new-tab", "--name", runtime_tab_name, "--layout", layout_file])


def close_tab(session_name: str, runtime_tab_name: str) -> None:
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


def is_task_running(task: DynamicTabTask) -> bool:
    tab = task["tab"]
    tab_for_check: TabConfig = {"tabName": task["runtime_tab_name"], "startDir": tab["startDir"], "command": tab["command"]}
    layout_for_check: LayoutConfig = {"layoutName": "dynamic-check", "layoutTabs": [tab_for_check]}
    status = check_command_status(tab_name=task["runtime_tab_name"], layout_config=layout_for_check)
    return status.get("running", False)
