from stackops.cluster.sessions_managers.session_conflict import SessionConflictAction
from stackops.scripts.python.helpers.helpers_sessions._tuios_backend_state import (
    list_session_entries,
    list_window_entries,
)
from stackops.scripts.python.helpers.helpers_sessions.sessions_dynamic_display import (
    DynamicStartResult,
    DynamicTabTask,
)
from stackops.scripts.python.helpers.helpers_sessions.sessions_tuios import run_layouts_with_tuios
from stackops.scripts.python.helpers.helpers_sessions.sessions_tuios_commands import close_window, launch_window
from stackops.utils.schemas.layouts.layout_types import LayoutConfig


def start_initial_session(
    initial_layout: LayoutConfig,
    on_conflict: SessionConflictAction,
) -> tuple[list[str], dict[str, DynamicStartResult]]:
    results, windows_by_session = run_layouts_with_tuios(
        layouts_selected=[initial_layout],
        on_conflict=on_conflict,
        exit_mode="backToShell",
    )
    start_results: dict[str, DynamicStartResult] = {}
    for name, result in results.items():
        if result["success"]:
            start_results[name] = {"success": True, "message": "TUIOS dynamic session started"}
        else:
            start_results[name] = {"success": False, "error": result.get("error", "TUIOS startup failed")}
    return list(windows_by_session), start_results


def spawn_tab(session_name: str, task: DynamicTabTask) -> None:
    launch_window(
        session_name=session_name,
        tab=task["tab"],
        exit_mode="backToShell",
    )


def close_tab(session_name: str, runtime_tab_name: str) -> None:
    for window in list_window_entries(session_name):
        if window.display_name == runtime_tab_name:
            close_window(session_name=session_name, window_id=window.window_id)
            return


def is_task_running(session_name: str, task: DynamicTabTask) -> bool:
    if not any(session.name == session_name and not session.saved for session in list_session_entries()):
        return False
    for window in list_window_entries(session_name):
        if window.display_name == task["runtime_tab_name"]:
            return not (window.at_prompt is True and window.command_seq > 0)
    return False
