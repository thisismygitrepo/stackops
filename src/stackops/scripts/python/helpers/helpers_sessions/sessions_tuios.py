import time

import typer

from stackops.cluster.sessions_managers.monitoring_types import StartResult
from stackops.cluster.sessions_managers.session_conflict import (
    SessionConflictAction,
    build_session_launch_plan,
    kill_existing_session,
)
from stackops.cluster.sessions_managers.session_exit_mode import SessionExitMode
from stackops.scripts.python.helpers.helpers_sessions._tuios_backend_state import (
    list_session_entries,
    list_window_entries,
    run_tuios,
)
from stackops.scripts.python.helpers.helpers_sessions.sessions_tuios_commands import (
    close_window,
    launch_window,
)
from stackops.utils.schemas.layouts.layout_types import LayoutConfig


def run_layouts_with_tuios(
    *,
    layouts_selected: list[LayoutConfig],
    on_conflict: SessionConflictAction,
    exit_mode: SessionExitMode,
) -> tuple[dict[str, StartResult], dict[str, tuple[str, ...]]]:
    for layout in layouts_selected:
        if not layout["layoutTabs"]:
            raise ValueError(f"""TUIOS cannot launch layout '{layout['layoutName']}' because it has no tabs.""")
    if layouts_selected and on_conflict in {"restart", "mergeOverwrite", "mergeSkip"}:
        if any(session.saved for session in list_session_entries()):
            run_tuios(["start-server"])
    plans = build_session_launch_plan(
        requested_session_names=[layout["layoutName"] for layout in layouts_selected],
        backend="tuios",
        on_conflict=on_conflict,
    )
    results: dict[str, StartResult] = {}
    launched_windows: dict[str, tuple[str, ...]] = {}
    for layout, plan in zip(layouts_selected, plans, strict=True):
        session_name = plan["session_name"]
        if plan.get("skip_launch", False):
            results[session_name] = {"success": True, "message": f"""Skipped existing TUIOS session '{session_name}'."""}
            continue
        if session_name != layout["layoutName"]:
            typer.echo(f"""Renaming TUIOS session '{layout['layoutName']}' to '{session_name}' to avoid a conflict.""")
        try:
            if plan["restart_required"]:
                kill_existing_session("tuios", session_name)
            merge_existing = on_conflict in {"mergeOverwrite", "mergeSkip"} and "conflict_source" in plan
            initial_window_ids: list[str] = []
            if not merge_existing:
                run_tuios(["new", "--detach", "--", session_name])
                initial_window_ids = [window.window_id for window in list_window_entries(session_name)]
            existing_windows = list_window_entries(session_name) if merge_existing else []
            window_ids = list(launched_windows.get(session_name, ()))
            for tab in layout["layoutTabs"]:
                matching_windows = [window for window in existing_windows if window.display_name == tab["tabName"]]
                if matching_windows and on_conflict == "mergeSkip":
                    continue
                window_ids.append(launch_window(session_name=session_name, tab=tab, exit_mode=exit_mode))
                for window in matching_windows:
                    close_window(session_name=session_name, window_id=window.window_id)
                    if window.window_id in window_ids:
                        window_ids.remove(window.window_id)
                if merge_existing:
                    existing_windows = list_window_entries(session_name)
            for window_id in initial_window_ids:
                close_window(session_name=session_name, window_id=window_id)
            launched_windows[session_name] = tuple(window_ids)
            message = f"""Started TUIOS session '{session_name}' with {len(window_ids)} window(s)."""
            results[session_name] = {"success": True, "message": message}
            typer.echo(message)
        except ValueError as error:
            results[session_name] = {"success": False, "error": str(error)}
    return results, launched_windows


def monitor_launched_windows(launched_windows: dict[str, tuple[str, ...]], poll_seconds: float) -> None:
    pending = {name: set(window_ids) for name, window_ids in launched_windows.items() if window_ids}
    while pending:
        existing_sessions = {session.name for session in list_session_entries() if not session.saved}
        for session_name in tuple(pending):
            if session_name not in existing_sessions:
                del pending[session_name]
                continue
            windows = {window.window_id: window for window in list_window_entries(session_name)}
            pending[session_name] = {
                window_id for window_id in pending[session_name]
                if window_id in windows and (
                    windows[window_id].command_seq == 0 or windows[window_id].at_prompt is not True
                )
            }
            if not pending[session_name]:
                del pending[session_name]
        if pending:
            time.sleep(poll_seconds)
