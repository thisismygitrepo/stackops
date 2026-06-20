from typing import Literal

from stackops.scripts.python.helpers.helpers_sessions._aoe_backend import (
    JsonObject,
    entry_text as _entry_text,
    list_session_entries as _session_entries,
    session_id as _session_id,
    session_preview as _session_preview,
    session_status as _session_status,
    session_title as _session_title,
)
from stackops.scripts.python.helpers.helpers_sessions._attach_common import (
    interactive_choose_with_preview,
    natural_sort_key,
)
from stackops.scripts.python.helpers.helpers_sessions.session_trace_models import (
    PaneCategory,
    TracePaneState,
    TraceSnapshot,
    TraceUntil,
    build_missing_snapshot,
)


SessionChoice = tuple[Literal["error", "session_name"], str]

_DONE_STATUSES = {
    "archived",
    "canceled",
    "cancelled",
    "closed",
    "complete",
    "completed",
    "done",
    "error",
    "failed",
    "finished",
    "stopped",
    "success",
    "succeeded",
}
_IDLE_STATUSES = {
    "idle",
    "not started",
    "paused",
    "ready",
    "snoozed",
    "waiting",
}
_RUNNING_STATUSES = {
    "active",
    "busy",
    "pending",
    "queued",
    "running",
    "starting",
    "working",
}
_EXIT_CODE_KEYS = (
    "exit_code",
    "exit_status",
    "command_exit_code",
    "terminal_exit_code",
    "exitCode",
    "exitStatus",
    "last_exit_code",
    "lastExitCode",
)


def _normalize_status(status: str | None) -> str:
    if status is None:
        return "unknown"
    return " ".join(status.strip().lower().replace("_", " ").replace("-", " ").split()) or "unknown"


def _entry_int(entry: JsonObject, key: str) -> int | None:
    value = entry.get(key)
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped_value = value.strip()
        if stripped_value.startswith("-") and stripped_value[1:].isdigit():
            return int(stripped_value)
        if stripped_value.isdigit():
            return int(stripped_value)
    return None


def _session_exit_code(session: JsonObject) -> int | None:
    for key in _EXIT_CODE_KEYS:
        exit_code = _entry_int(session, key)
        if exit_code is not None:
            return exit_code
    return None


def _session_identifier(session: JsonObject) -> str | None:
    return _session_title(session) or _session_id(session)


def _session_display_name(session: JsonObject) -> str:
    return _session_identifier(session) or "session"


def _session_match_values(session: JsonObject) -> set[str]:
    return {
        value
        for value in (
            _session_title(session),
            _entry_text(session, "name"),
            _session_id(session),
        )
        if value is not None
    }


def _find_session(sessions: list[JsonObject], session_name: str) -> tuple[JsonObject | None, str | None]:
    matching_sessions = [
        session
        for session in sessions
        if session_name in _session_match_values(session=session)
    ]
    if len(matching_sessions) == 0:
        return (None, None)
    if len(matching_sessions) > 1:
        return (
            matching_sessions[0],
            f"Multiple AoE sessions matched '{session_name}'; tracing the first match.",
        )
    return (matching_sessions[0], None)


def _session_category(status: str, exit_code: int | None) -> PaneCategory:
    if exit_code is not None or status in _DONE_STATUSES:
        return "exited"
    if status in _IDLE_STATUSES:
        return "idle-shell"
    if status in _RUNNING_STATUSES:
        return "running"
    return "unknown"


def _session_matches_criterion(
    *,
    category: PaneCategory,
    status: str,
    exit_code: int | None,
    until: TraceUntil,
    expected_exit_code: int | None,
) -> bool:
    match until:
        case "idle-shell":
            return category == "idle-shell" or status in _DONE_STATUSES
        case "all-exited":
            return category == "exited"
        case "exit-code":
            return category == "exited" and exit_code == expected_exit_code
        case "session-missing":
            return False


def _session_status_text(status: str, category: PaneCategory, exit_code: int | None) -> str:
    if exit_code is not None:
        return f"exited (code {exit_code})"
    if category == "idle-shell":
        return f"{status} session"
    if category == "running":
        return f"{status} session"
    if category == "exited":
        return status
    return status


def _session_process_name(session: JsonObject) -> str:
    return (
        _entry_text(session, "agent", "tool", "command", "cmd", "display_agent")
        or "aoe"
    )


def _session_cwd(session: JsonObject) -> str:
    return (
        _entry_text(session, "path", "project_path", "projectPath", "workspace", "cwd", "start_dir", "startDir")
        or "—"
    )


def _session_is_active(session: JsonObject, category: PaneCategory) -> bool:
    running = session.get("running")
    if isinstance(running, bool):
        return running
    return category == "running"


def _build_option_maps(sessions: list[JsonObject]) -> tuple[dict[str, str], dict[str, str]]:
    label_counts: dict[str, int] = {}
    for session in sessions:
        label = _session_display_name(session=session)
        label_counts[label] = label_counts.get(label, 0) + 1

    options_to_trace_target: dict[str, str] = {}
    options_to_preview_mapping: dict[str, str] = {}
    for session in sessions:
        identifier = _session_identifier(session=session)
        if identifier is None:
            continue
        label = _session_display_name(session=session)
        trace_target = identifier
        if label_counts[label] > 1:
            session_id = _session_id(session)
            label = f"{label} ({session_id})" if session_id is not None else label
            trace_target = session_id or identifier
        options_to_trace_target[label] = trace_target
        options_to_preview_mapping[label] = _session_preview(session)
    return options_to_trace_target, options_to_preview_mapping


def choose_existing_session_name(
    msg: str = "Choose an AoE session to trace:",
) -> SessionChoice:
    sessions = _session_entries()
    if sessions is None:
        return ("error", "Could not read AoE sessions. Is `aoe` installed?")
    if len(sessions) == 0:
        return ("error", "No AoE sessions are available.")

    sessions.sort(key=lambda session: natural_sort_key(_session_display_name(session=session)))
    option_to_trace_target, options_to_preview_mapping = _build_option_maps(sessions=sessions)
    chosen_label = interactive_choose_with_preview(
        msg=msg,
        options_to_preview_mapping=options_to_preview_mapping,
    )
    if chosen_label is None:
        return ("error", "No AoE session selected.")
    trace_target = option_to_trace_target.get(chosen_label)
    if trace_target is None:
        return ("error", f"Unknown AoE session selected: {chosen_label}")
    return ("session_name", trace_target)


def evaluate_trace_snapshot(
    session_name: str,
    session: JsonObject,
    until: TraceUntil,
    expected_exit_code: int | None,
    pane_warning: str | None,
) -> TraceSnapshot:
    status = _normalize_status(_session_status(session))
    exit_code = _session_exit_code(session=session)
    category = _session_category(status=status, exit_code=exit_code)
    matched = _session_matches_criterion(
        category=category,
        status=status,
        exit_code=exit_code,
        until=until,
        expected_exit_code=expected_exit_code,
    )
    pane_state = TracePaneState(
        window_index="1",
        window_name=_entry_text(session, "group", "group_path", "groupPath") or _session_display_name(session=session),
        pane_index=_session_id(session) or _session_title(session) or "session",
        process_name=_session_process_name(session=session),
        status_text=_session_status_text(status=status, category=category, exit_code=exit_code),
        cwd=_session_cwd(session=session),
        is_active=_session_is_active(session=session, category=category),
        category=category,
        exit_code=exit_code,
        matched=matched,
    )
    return TraceSnapshot(
        session_name=session_name,
        session_exists=True,
        total_windows=1,
        panes=(pane_state,),
        total_targets=1,
        matched_targets=1 if matched else 0,
        pane_warning=pane_warning,
        session_error=None,
        criterion_satisfied=matched,
        idle_shell_panes=1 if category == "idle-shell" else 0,
        running_panes=1 if category == "running" else 0,
        exited_panes=1 if category == "exited" else 0,
        unknown_panes=1 if category == "unknown" else 0,
    )


def load_trace_snapshot(
    session_name: str,
    until: TraceUntil,
    expected_exit_code: int | None,
) -> TraceSnapshot:
    sessions = _session_entries()
    if sessions is None:
        return build_missing_snapshot(
            session_name=session_name,
            until=until,
            session_error="Could not read AoE sessions. Is `aoe` installed?",
        )

    session, session_warning = _find_session(sessions=sessions, session_name=session_name)
    if session is None:
        return build_missing_snapshot(
            session_name=session_name,
            until=until,
            session_error="AoE session is missing.",
        )

    return evaluate_trace_snapshot(
        session_name=session_name,
        session=session,
        until=until,
        expected_exit_code=expected_exit_code,
        pane_warning=session_warning,
    )
