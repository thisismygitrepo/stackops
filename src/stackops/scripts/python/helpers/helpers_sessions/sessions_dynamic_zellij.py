from stackops.cluster.sessions_managers.session_conflict import SessionConflictAction
from stackops.scripts.python.helpers.helpers_sessions._zellij_backend_idle import pane_is_idle
from stackops.scripts.python.helpers.helpers_sessions._zellij_backend_state import (
    list_pane_entries,
    list_session_names,
    list_tab_entries,
    run_zellij,
)
from stackops.scripts.python.helpers.helpers_sessions.sessions_dynamic_display import DynamicStartResult, DynamicTabTask
from stackops.scripts.python.helpers.helpers_sessions.sessions_zellij import run_layouts_with_zellij
from stackops.scripts.python.helpers.helpers_sessions.sessions_zellij_layout import launch_tab
from stackops.utils.schemas.layouts.layout_types import LayoutConfig


def start_initial_session(
    initial_layout: LayoutConfig,
    on_conflict: SessionConflictAction,
) -> tuple[list[str], dict[str, DynamicStartResult]]:
    results, panes_by_session = run_layouts_with_zellij(
        layouts_selected=[initial_layout],
        on_conflict=on_conflict,
        exit_mode="backToShell",
    )
    start_results: dict[str, DynamicStartResult] = {}
    for name, result in results.items():
        if result["success"]:
            start_results[name] = {"success": True, "message": "Zellij dynamic session started"}
        else:
            start_results[name] = {"success": False, "error": result.get("error", "Zellij startup failed")}
    return list(panes_by_session), start_results


def spawn_tab(session_name: str, task: DynamicTabTask) -> None:
    launch_tab(session_name=session_name, tab=task["tab"], exit_mode="backToShell")


def close_tab(session_name: str, runtime_tab_name: str) -> None:
    if session_name not in list_session_names():
        return
    for tab in list_tab_entries(session_name):
        if tab.name == runtime_tab_name:
            run_zellij(["--session", session_name, "action", "close-tab", "--tab-id", str(tab.tab_id)])


def is_task_running(session_name: str, task: DynamicTabTask) -> bool:
    if session_name not in list_session_names():
        return False
    return any(
        not pane.exited and pane_is_idle(pane) is not True
        for pane in list_pane_entries(session_name)
        if pane.tab_name == task["runtime_tab_name"]
    )
