from dataclasses import replace

from stackops.scripts.python.helpers.helpers_sessions._tuios_backend_idle import window_is_idle
from stackops.scripts.python.helpers.helpers_sessions._tuios_backend_models import WindowEntry
from stackops.scripts.python.helpers.helpers_sessions._tuios_backend_state import (
    list_session_entries,
    list_window_entries,
)
from stackops.scripts.python.helpers.helpers_sessions.session_trace_models import (
    PaneCategory,
    TracePaneState,
    TraceSnapshot,
    TraceTarget,
    TraceUntil,
    build_missing_snapshot,
)


def list_trace_targets() -> tuple[list[TraceTarget] | None, str | None]:
    try:
        sessions = list_session_entries()
    except ValueError as error:
        return None, str(error)
    return [
        TraceTarget(label=session.name, session_name=session.name, match_names=(session.name,))
        for session in sessions if not session.saved
    ], None


def _window_trace_state(session_name: str, window: WindowEntry, until: TraceUntil, expected_exit_code: int | None) -> TracePaneState:
    category: PaneCategory = "unknown"
    status = "unknown"
    completed = window.at_prompt is True and window.command_seq > 0
    if window.at_prompt is True:
        category = "idle-shell"
        status = "idle shell"
        if completed and until in {"all-exited", "exit-code"}:
            category = "exited"
            status = f"""command exited (code {window.last_exit_code if window.last_exit_code is not None else 'unknown'})"""
    elif window.at_prompt is False or window.agent_state in {"working", "needs_input", "idle", "done", "errored"}:
        category = "running"
        status = f"""agent: {window.agent_state}""" if window.agent_state != "none" else "running"
    if until == "idle-shell":
        idle = window_is_idle(session_name=session_name, window=window)
        category = "idle-shell" if idle is True else "running" if idle is False else "unknown"
        status = "idle shell" if idle is True else "running" if idle is False else "unknown"
        if idle is False and window.agent_state != "none":
            status = f"""agent: {window.agent_state}"""
    matched = False
    match until:
        case "idle-shell":
            matched = category == "idle-shell"
        case "all-exited":
            matched = completed
        case "exit-code":
            matched = completed and window.last_exit_code == expected_exit_code
        case "session-missing":
            pass
    return TracePaneState(
        window_index=str(window.index),
        window_name=window.display_name,
        window_target=window.window_id,
        pane_index=str(window.index),
        pane_target=window.window_id,
        process_name=window.running_command or window.foreground_command or window.last_command or "—",
        status_text=status,
        cwd=window.cwd or "—",
        is_active=window.focused,
        category=category,
        exit_code=window.last_exit_code if completed else None,
        matched=matched,
    )


def load_trace_snapshot(session_name: str, until: TraceUntil, expected_exit_code: int | None) -> TraceSnapshot:
    try:
        sessions = list_session_entries()
    except ValueError as error:
        return replace(
            build_missing_snapshot(session_name=session_name, until=until, session_error=str(error)),
            criterion_satisfied=False,
            matched_targets=0,
        )
    if not any(session.name == session_name and not session.saved for session in sessions):
        return build_missing_snapshot(session_name=session_name, until=until, session_error="TUIOS session is missing.")
    warning: str | None = None
    try:
        windows = list_window_entries(session_name=session_name)
    except ValueError as error:
        windows = []
        warning = str(error)
    panes = tuple(_window_trace_state(session_name, window, until, expected_exit_code) for window in windows)
    if until in {"all-exited", "exit-code"} and any(window.at_prompt is None for window in windows):
        warning = "Shell status requires OSC 133 integration; commands launched through StackOps report it automatically."
    matched_targets = sum(pane.matched for pane in panes)
    return TraceSnapshot(
        session_name=session_name,
        session_target=session_name,
        session_exists=True,
        total_windows=len(windows),
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
