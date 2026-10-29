from stackops.cluster.sessions_managers.session_conflict import SessionConflictAction
from stackops.scripts.python.helpers.helpers_sessions._tuios_backend_state import (
    free_workspace_number,
    list_session_entries,
    list_window_entries,
    list_workspace_entries,
)
from stackops.scripts.python.helpers.helpers_sessions._tuios_backend_models import WindowEntry
from stackops.scripts.python.helpers.helpers_sessions.sessions_dynamic_display import (
    DynamicStartResult,
    DynamicTabTask,
)
from stackops.scripts.python.helpers.helpers_sessions.sessions_tuios import run_layouts_with_tuios
from stackops.scripts.python.helpers.helpers_sessions.sessions_tuios_commands import close_window, launch_tab
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
    launch_tab(
        session_name=session_name,
        tab=task["tab"],
        exit_mode="backToShell",
        workspace=free_workspace_number(session_name=session_name, ignored_window_ids=frozenset()),
    )


def _tab_windows(session_name: str, runtime_tab_name: str) -> list[WindowEntry]:
    workspace_numbers = {
        workspace.number for workspace in list_workspace_entries(session_name) if workspace.name == runtime_tab_name
    }
    return [window for window in list_window_entries(session_name) if window.workspace in workspace_numbers]


def close_tab(session_name: str, runtime_tab_name: str) -> None:
    for window in _tab_windows(session_name=session_name, runtime_tab_name=runtime_tab_name):
        close_window(session_name=session_name, window_id=window.window_id)


def is_task_running(session_name: str, task: DynamicTabTask) -> bool:
    if not any(session.name == session_name and not session.saved for session in list_session_entries()):
        return False
    windows = _tab_windows(session_name=session_name, runtime_tab_name=task["runtime_tab_name"])
    return any(not (window.at_prompt is True and window.command_seq > 0) for window in windows)
