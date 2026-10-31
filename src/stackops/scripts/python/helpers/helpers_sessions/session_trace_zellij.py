from dataclasses import replace

from stackops.scripts.python.helpers.helpers_sessions._zellij_backend_idle import pane_is_idle
from stackops.scripts.python.helpers.helpers_sessions._zellij_backend_models import PaneEntry
from stackops.scripts.python.helpers.helpers_sessions._zellij_backend_state import (
    list_pane_entries,
    list_session_names,
    list_tab_entries,
)
from stackops.scripts.python.helpers.helpers_sessions.session_trace_models import (
    PaneCategory,
    TracePaneState,
    TraceSnapshot,
    TraceTarget,
    TraceUntil,
    build_missing_snapshot,
    pane_matches_criterion,
)
from stackops.scripts.python.helpers.helpers_sessions.sessions_zellij_commands import original_command, original_start_dir


def list_trace_targets() -> tuple[list[TraceTarget] | None, str | None]:
    try:
        names = list_session_names()
    except ValueError as error:
        return None, str(error)
    return [TraceTarget(label=name, session_name=name, match_names=(name,)) for name in names], None


def _pane_trace_state(pane: PaneEntry, until: TraceUntil, expected_exit_code: int | None) -> TracePaneState:
    category: PaneCategory
    if pane.exited:
        category = "exited"
        status = f"""exited (code {pane.exit_status if pane.exit_status is not None else 'unknown'})"""
    elif pane.is_held:
        category = "unknown"
        status = "suspended"
    else:
        idle = pane_is_idle(pane=pane)
        category = "idle-shell" if idle is True else "running" if idle is False else "unknown"
        status = "idle shell" if idle is True else "running" if idle is False else "unknown"
    return TracePaneState(
        window_index=str(pane.tab_position),
        window_name=pane.tab_name,
        window_target=str(pane.tab_id),
        pane_index=pane.pane_id.removeprefix("terminal_"),
        pane_target=pane.pane_id,
        process_name=original_command(terminal_command=pane.command or pane.terminal_command) or pane.title or "—",
        status_text=status,
        cwd=pane.cwd or original_start_dir(terminal_command=pane.terminal_command) or "—",
        is_active=pane.focused,
        category=category,
        exit_code=pane.exit_status if pane.exited else None,
        matched=pane_matches_criterion(
            category=category,
            pane_exit_code=pane.exit_status,
            until=until,
            expected_exit_code=expected_exit_code,
        ),
    )


def load_trace_snapshot(session_name: str, until: TraceUntil, expected_exit_code: int | None) -> TraceSnapshot:
    try:
        session_names = list_session_names()
    except ValueError as error:
        return replace(
            build_missing_snapshot(session_name=session_name, until=until, session_error=str(error)),
            criterion_satisfied=False,
            matched_targets=0,
        )
    if session_name not in session_names:
        return build_missing_snapshot(session_name=session_name, until=until, session_error="Zellij session is missing.")
    warning: str | None = None
    total_windows = 0
    panes: tuple[TracePaneState, ...] = ()
    try:
        total_windows = len(list_tab_entries(session_name=session_name))
        panes = tuple(
            _pane_trace_state(pane=pane, until=until, expected_exit_code=expected_exit_code)
            for pane in list_pane_entries(session_name=session_name)
        )
    except ValueError as error:
        warning = str(error)
    matched_targets = sum(pane.matched for pane in panes)
    return TraceSnapshot(
        session_name=session_name,
        session_target=session_name,
        session_exists=True,
        total_windows=total_windows,
        panes=panes,
        total_targets=len(panes),
        matched_targets=matched_targets,
        pane_warning=warning,
        session_error=None,
        criterion_satisfied=bool(panes) and matched_targets == len(panes),
        idle_shell_panes=sum(pane.category == "idle-shell" for pane in panes),
        running_panes=sum(pane.category == "running" for pane in panes),
        exited_panes=sum(pane.category == "exited" for pane in panes),
        unknown_panes=sum(pane.category == "unknown" for pane in panes),
    )
