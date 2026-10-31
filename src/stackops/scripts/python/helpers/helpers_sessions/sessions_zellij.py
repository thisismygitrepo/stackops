import time

import typer

from stackops.cluster.sessions_managers.monitoring_types import StartResult
from stackops.cluster.sessions_managers.session_conflict import SessionConflictAction, build_session_launch_plan
from stackops.cluster.sessions_managers.session_exit_mode import SessionExitMode
from stackops.cluster.sessions_managers.session_launch_table import LaunchedPaneRow, print_launch_table
from stackops.scripts.python.helpers.helpers_sessions._zellij_backend_idle import pane_is_idle
from stackops.scripts.python.helpers.helpers_sessions._zellij_backend_models import PaneEntry
from stackops.scripts.python.helpers.helpers_sessions._zellij_backend_state import (
    list_pane_entries,
    list_session_entries,
    list_session_names,
    list_tab_entries,
    run_zellij,
)
from stackops.scripts.python.helpers.helpers_sessions.sessions_zellij_constants import STARTUP_POLL_SECONDS, STARTUP_TIMEOUT_SECONDS
from stackops.scripts.python.helpers.helpers_sessions.sessions_zellij_layout import launch_session, launch_tab, layout_kdl, wait_for_session
from stackops.utils.schemas.layouts.layout_types import LayoutConfig, TabConfig


def _remove_session_for_restart(session_name: str) -> None:
    if session_name in list_session_names():
        run_zellij(["kill-session", "--", session_name])
        deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
        while session_name in list_session_names():
            if time.monotonic() >= deadline:
                raise ValueError(f"""Zellij session '{session_name}' did not stop before restart.""")
            time.sleep(STARTUP_POLL_SECONDS)
    if any(session.name == session_name for session in list_session_entries()):
        run_zellij(["delete-session", "--", session_name])


def run_layouts_with_zellij(
    layouts_selected: list[LayoutConfig],
    on_conflict: SessionConflictAction,
    exit_mode: SessionExitMode,
) -> tuple[dict[str, StartResult], dict[str, tuple[str, ...]]]:
    for layout in layouts_selected:
        layout_kdl(layout=layout, exit_mode=exit_mode)
    plans = build_session_launch_plan(
        requested_session_names=[layout["layoutName"] for layout in layouts_selected],
        backend="zellij",
        on_conflict=on_conflict,
    )
    results: dict[str, StartResult] = {}
    launched_panes: dict[str, tuple[str, ...]] = {}
    for layout, plan in zip(layouts_selected, plans, strict=True):
        session_name = plan["session_name"]
        if plan.get("skip_launch", False):
            results[session_name] = {"success": True, "message": f"""Skipped existing Zellij session '{session_name}'."""}
            continue
        if session_name != layout["layoutName"]:
            typer.echo(f"""Renaming Zellij session '{layout['layoutName']}' to '{session_name}' to avoid a conflict.""")
        try:
            if plan["restart_required"]:
                _remove_session_for_restart(session_name)
            merge_existing = on_conflict in {"mergeOverwrite", "mergeSkip"} and "conflict_source" in plan
            panes: list[PaneEntry]
            launched_tabs: list[TabConfig]
            if merge_existing:
                if session_name not in list_session_names():
                    run_zellij(["attach", "--create-background", "--", session_name])
                    wait_for_session(session_name)
                panes = []
                launched_tabs = []
                for tab in layout["layoutTabs"]:
                    matching_tabs = [entry for entry in list_tab_entries(session_name) if entry.name == tab["tabName"]]
                    if matching_tabs and on_conflict == "mergeSkip":
                        continue
                    panes.extend(launch_tab(session_name=session_name, tab=tab, exit_mode=exit_mode))
                    launched_tabs.append(tab)
                    for replaced_tab in matching_tabs:
                        run_zellij(["--session", session_name, "action", "close-tab", "--tab-id", str(replaced_tab.tab_id)])
            else:
                panes = launch_session(session_name=session_name, layout=layout, exit_mode=exit_mode)
                launched_tabs = layout["layoutTabs"]
            if launched_tabs:
                pane_ids = set(launched_panes.get(session_name, ())) | {pane.pane_id for pane in panes}
                launched_panes[session_name] = tuple(pane_ids)
            results[session_name] = {"success": True, "message": f"""Started Zellij session '{session_name}' with {len(launched_tabs)} tab(s)."""}
            print_launch_table(
                backend="zellij",
                session_name=session_name,
                rows=[
                    LaunchedPaneRow(
                        location=str(index + 1),
                        tab_name=tab["tabName"],
                        pane_name=pane["paneName"],
                        handle=next((entry.pane_id for entry in panes if entry.tab_name == tab["tabName"] and entry.title == pane["paneName"]), "exited"),
                        command=pane["command"],
                        start_dir=pane["startDir"],
                    )
                    for index, tab in enumerate(launched_tabs) for pane in tab["panes"]
                ],
                verb="started",
            )
        except ValueError as error:
            results[session_name] = {"success": False, "error": str(error)}
    return results, launched_panes


def monitor_launched_panes(launched_panes: dict[str, tuple[str, ...]], poll_seconds: float) -> None:
    pending = {name: set(pane_ids) for name, pane_ids in launched_panes.items() if pane_ids}
    while pending:
        sessions = set(list_session_names())
        for session_name in tuple(pending):
            if session_name not in sessions:
                del pending[session_name]
                continue
            pending[session_name].intersection_update(
                pane.pane_id for pane in list_pane_entries(session_name)
                if not pane.exited and pane_is_idle(pane) is not True
            )
            if not pending[session_name]:
                del pending[session_name]
        if pending:
            time.sleep(poll_seconds)
