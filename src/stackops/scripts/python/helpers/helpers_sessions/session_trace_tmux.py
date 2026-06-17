from stackops.cluster.sessions_managers.tmux.tmux_utils.tmux_status import (
    check_tmux_session_status,
)
from stackops.scripts.python.helpers.helpers_sessions.session_trace_models import (
    PaneCategory,
    TracePaneState,
    TraceSnapshot,
    TraceUntil,
    build_missing_snapshot,
    pane_matches_criterion,
)
from stackops.scripts.python.helpers.helpers_sessions._tmux_backend_preview import (
    collect_session_snapshot,
)
from stackops.scripts.python.helpers.helpers_sessions._tmux_backend_processes import (
    classify_pane_status,
    find_meaningful_pane_process_label,
)
from stackops.scripts.python.helpers.helpers_sessions._attach_common import run_command


def _classify_status_text(status_text: str) -> PaneCategory:
    if status_text == "idle shell":
        return "idle-shell"
    if status_text.startswith("running:"):
        return "running"
    if status_text.startswith("exited (code "):
        return "exited"
    return "unknown"


def _parse_exit_code(value: str) -> int | None:
    stripped_value = value.strip()
    if stripped_value.startswith("-"):
        maybe_digits = stripped_value[1:]
        if maybe_digits.isdigit():
            return int(stripped_value)
        return None
    if stripped_value.isdigit():
        return int(stripped_value)
    return None


def evaluate_trace_snapshot(
    session_name: str,
    windows: list[dict[str, str]],
    panes_by_window: dict[str, list[dict[str, str]]],
    until: TraceUntil,
    expected_exit_code: int | None,
    pane_warning: str | None,
) -> TraceSnapshot:
    pane_states: list[TracePaneState] = []
    idle_shell_panes = 0
    running_panes = 0
    exited_panes = 0
    unknown_panes = 0

    for window in windows:
        window_panes = panes_by_window.get(window["window_index"], [])
        for pane in window_panes:
            process_name, status_text = classify_pane_status(
                pane,
                pane_process_label_finder=find_meaningful_pane_process_label,
            )
            category = _classify_status_text(status_text=status_text)
            pane_exit_code = _parse_exit_code(pane.get("pane_dead_status", ""))
            matched = pane_matches_criterion(
                category=category,
                pane_exit_code=pane_exit_code,
                until=until,
                expected_exit_code=expected_exit_code,
            )
            match category:
                case "idle-shell":
                    idle_shell_panes += 1
                case "running":
                    running_panes += 1
                case "exited":
                    exited_panes += 1
                case "unknown":
                    unknown_panes += 1
            pane_states.append(
                TracePaneState(
                    window_index=window["window_index"],
                    window_name=window["window_name"],
                    pane_index=pane["pane_index"],
                    process_name=process_name,
                    status_text=status_text,
                    cwd=pane["pane_cwd"] or "—",
                    is_active=bool(pane["pane_active"]),
                    category=category,
                    exit_code=pane_exit_code,
                    matched=matched,
                )
            )

    total_targets = len(pane_states)
    matched_targets = sum(1 for pane in pane_states if pane.matched)
    return TraceSnapshot(
        session_name=session_name,
        session_exists=True,
        total_windows=len(windows),
        panes=tuple(pane_states),
        total_targets=total_targets,
        matched_targets=matched_targets,
        pane_warning=pane_warning,
        session_error=None,
        criterion_satisfied=total_targets > 0 and matched_targets == total_targets,
        idle_shell_panes=idle_shell_panes,
        running_panes=running_panes,
        exited_panes=exited_panes,
        unknown_panes=unknown_panes,
    )


def load_trace_snapshot(
    session_name: str,
    until: TraceUntil,
    expected_exit_code: int | None,
) -> TraceSnapshot:
    session_status = check_tmux_session_status(session_name=session_name)
    if session_status["session_exists"] is False:
        return build_missing_snapshot(
            session_name=session_name,
            until=until,
            session_error=session_status.get("error"),
        )

    windows, panes_by_window, pane_warning = collect_session_snapshot(
        session_name=session_name,
        run_command_fn=run_command,
    )
    if windows is None:
        return build_missing_snapshot(
            session_name=session_name,
            until=until,
            session_error=pane_warning,
        )

    return evaluate_trace_snapshot(
        session_name=session_name,
        windows=windows,
        panes_by_window=panes_by_window,
        until=until,
        expected_exit_code=expected_exit_code,
        pane_warning=pane_warning,
    )
