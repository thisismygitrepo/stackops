import json
from typing import Any, Literal, cast

from stackops.scripts.python.helpers.helpers_sessions._attach_common import (
    interactive_choose_with_preview,
    natural_sort_key,
    run_command,
)
from stackops.scripts.python.helpers.helpers_sessions.session_trace_models import (
    PaneCategory,
    TracePaneState,
    TraceSnapshot,
    TraceUntil,
    build_missing_snapshot,
)


JsonObject = dict[str, Any]
WorkspaceChoice = tuple[Literal["error", "session_name"], str]

_DONE_AGENT_STATUSES = {"done"}
_IDLE_AGENT_STATUSES = {"idle"}
_RUNNING_AGENT_STATUSES = {"working", "blocked"}
_EXIT_CODE_KEYS = (
    "exit_code",
    "exit_status",
    "command_exit_code",
    "terminal_exit_code",
)


def _run_herdr_json(args: list[str]) -> tuple[JsonObject | None, str | None]:
    try:
        result = run_command(args)
    except FileNotFoundError:
        return (None, "Herdr backend requested, but `herdr` was not found in PATH.")
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "unknown error").strip()
        return (None, detail)
    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError:
        return (None, "Herdr command returned invalid JSON.")
    if not isinstance(parsed, dict):
        return (None, "Herdr command returned non-object JSON.")
    return (cast(JsonObject, parsed), None)


def _dict_entries(value: object) -> list[JsonObject]:
    if not isinstance(value, list):
        return []
    return [cast(JsonObject, item) for item in value if isinstance(item, dict)]


def _result_entries(payload: JsonObject | None, key: str) -> list[JsonObject]:
    if payload is None:
        return []
    result = payload.get("result")
    if not isinstance(result, dict):
        return []
    return _dict_entries(result.get(key))


def _entry_text(entry: JsonObject, key: str) -> str | None:
    value = entry.get(key)
    if isinstance(value, str) and value:
        return value
    return None


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


def _load_workspaces() -> tuple[list[JsonObject] | None, str | None]:
    payload, error = _run_herdr_json(["herdr", "workspace", "list"])
    if payload is None:
        return (None, error)
    workspaces = _result_entries(payload, "workspaces")
    workspaces.sort(
        key=lambda workspace: (
            not bool(workspace.get("focused")),
            _entry_int(workspace, "number") or 0,
            natural_sort_key(_workspace_display_name(workspace)),
        )
    )
    return (workspaces, None)


def _load_tabs(workspace_id: str) -> tuple[list[JsonObject] | None, str | None]:
    payload, error = _run_herdr_json(["herdr", "tab", "list", "--workspace", workspace_id])
    if payload is None:
        return (None, error)
    tabs = _result_entries(payload, "tabs")
    tabs.sort(key=_tab_sort_key)
    return (tabs, None)


def _load_panes(workspace_id: str) -> tuple[list[JsonObject] | None, str | None]:
    payload, error = _run_herdr_json(["herdr", "pane", "list", "--workspace", workspace_id])
    if payload is None:
        return (None, error)
    return (_result_entries(payload, "panes"), None)


def _workspace_display_name(workspace: JsonObject) -> str:
    return (
        _entry_text(workspace, "label")
        or _entry_text(workspace, "workspace_id")
        or "workspace"
    )


def _workspace_id(workspace: JsonObject) -> str | None:
    return _entry_text(workspace, "workspace_id")


def _workspace_matches_name(workspace: JsonObject, session_name: str) -> bool:
    return session_name in {
        _entry_text(workspace, "label"),
        _entry_text(workspace, "workspace_id"),
    }


def _find_workspace(workspaces: list[JsonObject], session_name: str) -> tuple[JsonObject | None, str | None]:
    matching_workspaces = [
        workspace
        for workspace in workspaces
        if _workspace_matches_name(workspace=workspace, session_name=session_name)
    ]
    if len(matching_workspaces) == 0:
        return (None, None)
    if len(matching_workspaces) > 1:
        return (
            matching_workspaces[0],
            f"Multiple Herdr workspaces matched '{session_name}'; tracing the first match.",
        )
    return (matching_workspaces[0], None)


def _tab_sort_key(tab: JsonObject) -> tuple[int, str]:
    number = _entry_int(tab, "number")
    return (number if number is not None else 999_999, _tab_id(tab) or "")


def _tab_id(tab: JsonObject) -> str | None:
    return _entry_text(tab, "tab_id")


def _tab_index(tab: JsonObject) -> str:
    number = _entry_int(tab, "number")
    if number is not None:
        return str(number)
    return _tab_id(tab) or "?"


def _tab_name(tab: JsonObject) -> str:
    return _entry_text(tab, "label") or _tab_id(tab) or "tab"


def _pane_sort_key(pane: JsonObject) -> tuple[str, str]:
    return (
        _entry_text(pane, "tab_id") or "",
        _entry_text(pane, "pane_id") or "",
    )


def _pane_exit_code(pane: JsonObject) -> int | None:
    for key in _EXIT_CODE_KEYS:
        exit_code = _entry_int(pane, key)
        if exit_code is not None:
            return exit_code
    return None


def _pane_agent_status(pane: JsonObject, tab: JsonObject | None) -> str:
    return (
        _entry_text(pane, "agent_status")
        or (None if tab is None else _entry_text(tab, "agent_status"))
        or "unknown"
    ).lower()


def _pane_category(agent_status: str, exit_code: int | None) -> PaneCategory:
    if exit_code is not None or agent_status in _DONE_AGENT_STATUSES:
        return "exited"
    if agent_status in _IDLE_AGENT_STATUSES:
        return "idle-shell"
    if agent_status in _RUNNING_AGENT_STATUSES:
        return "running"
    return "unknown"


def _pane_process_name(pane: JsonObject) -> str:
    return (
        _entry_text(pane, "agent")
        or _entry_text(pane, "display_agent")
        or _entry_text(pane, "label")
        or _entry_text(pane, "terminal_id")
        or "herdr"
    )


def _pane_status_text(agent_status: str, category: PaneCategory, exit_code: int | None) -> str:
    if exit_code is not None:
        return f"exited (code {exit_code})"
    if category == "exited":
        return "done"
    if category == "idle-shell":
        return "idle agent"
    if category == "running":
        return f"{agent_status} agent"
    return agent_status


def _pane_matches_criterion(
    *,
    category: PaneCategory,
    agent_status: str,
    exit_code: int | None,
    until: TraceUntil,
    expected_exit_code: int | None,
) -> bool:
    match until:
        case "idle-shell":
            return category == "idle-shell" or agent_status in _DONE_AGENT_STATUSES
        case "all-exited":
            return category == "exited"
        case "exit-code":
            return category == "exited" and exit_code == expected_exit_code
        case "session-missing":
            return False


def _build_workspace_preview(workspace: JsonObject) -> str:
    lines = [
        "backend: herdr",
        f"workspace: {_workspace_display_name(workspace)}",
        f"id: {_workspace_id(workspace) or ''}",
        f"focused: {'yes' if workspace.get('focused') else 'no'}",
    ]
    agent_status = _entry_text(workspace, "agent_status")
    if agent_status is not None:
        lines.append(f"agent status: {agent_status}")
    tab_count = _entry_int(workspace, "tab_count")
    pane_count = _entry_int(workspace, "pane_count")
    if tab_count is not None:
        lines.append(f"tabs: {tab_count}")
    if pane_count is not None:
        lines.append(f"panes: {pane_count}")
    return "\n".join(lines)


def choose_existing_workspace_name(
    msg: str = "Choose a Herdr workspace to trace:",
) -> WorkspaceChoice:
    workspaces, error = _load_workspaces()
    if workspaces is None:
        return ("error", error or "Unable to list Herdr workspaces.")
    if len(workspaces) == 0:
        return ("error", "No Herdr workspaces are available.")

    workspace_label_counts: dict[str, int] = {}
    for workspace in workspaces:
        workspace_label = _workspace_display_name(workspace)
        workspace_label_counts[workspace_label] = workspace_label_counts.get(workspace_label, 0) + 1

    labels_to_workspaces: dict[str, JsonObject] = {}
    labels_to_trace_target: dict[str, str] = {}
    for workspace in workspaces:
        workspace_label = _workspace_display_name(workspace)
        workspace_id = _workspace_id(workspace)
        label = workspace_label
        trace_target = workspace_label
        if workspace_label_counts[workspace_label] > 1:
            label = f"{workspace_label} ({workspace_id})" if workspace_id is not None else workspace_label
            trace_target = workspace_id or workspace_label
        labels_to_workspaces[label] = workspace
        labels_to_trace_target[label] = trace_target

    chosen_label = interactive_choose_with_preview(
        msg=msg,
        options_to_preview_mapping={
            label: _build_workspace_preview(workspace)
            for label, workspace in labels_to_workspaces.items()
        },
    )
    if chosen_label is None:
        return ("error", "No Herdr workspace selected.")
    chosen_workspace = labels_to_workspaces.get(chosen_label)
    if chosen_workspace is None:
        return ("error", f"Unknown Herdr workspace selected: {chosen_label}")
    return ("session_name", labels_to_trace_target[chosen_label])


def load_trace_snapshot(
    session_name: str,
    until: TraceUntil,
    expected_exit_code: int | None,
) -> TraceSnapshot:
    workspaces, workspace_error = _load_workspaces()
    if workspaces is None:
        return build_missing_snapshot(
            session_name=session_name,
            until=until,
            session_error=workspace_error,
        )

    workspace, workspace_warning = _find_workspace(workspaces=workspaces, session_name=session_name)
    if workspace is None:
        return build_missing_snapshot(
            session_name=session_name,
            until=until,
            session_error="Herdr workspace is missing.",
        )
    workspace_id = _workspace_id(workspace)
    if workspace_id is None:
        return build_missing_snapshot(
            session_name=session_name,
            until=until,
            session_error="Matched Herdr workspace did not include a workspace_id.",
        )

    tabs, tab_error = _load_tabs(workspace_id)
    panes, pane_error = _load_panes(workspace_id)
    if tabs is None:
        tabs = []
    if panes is None:
        panes = []

    warnings = [
        warning
        for warning in (workspace_warning, tab_error, pane_error)
        if warning is not None and warning.strip()
    ]
    pane_warning = "; ".join(warnings) if warnings else None
    return evaluate_trace_snapshot(
        session_name=session_name,
        tabs=tabs,
        panes=panes,
        until=until,
        expected_exit_code=expected_exit_code,
        pane_warning=pane_warning,
    )


def evaluate_trace_snapshot(
    session_name: str,
    tabs: list[JsonObject],
    panes: list[JsonObject],
    until: TraceUntil,
    expected_exit_code: int | None,
    pane_warning: str | None,
) -> TraceSnapshot:
    tab_by_id = {
        tab_id: tab
        for tab in tabs
        if (tab_id := _tab_id(tab)) is not None
    }
    panes_sorted = sorted(panes, key=_pane_sort_key)
    pane_states: list[TracePaneState] = []
    idle_shell_panes = 0
    running_panes = 0
    exited_panes = 0
    unknown_panes = 0

    for pane in panes_sorted:
        tab_id = _entry_text(pane, "tab_id")
        tab = tab_by_id.get(tab_id or "")
        agent_status = _pane_agent_status(pane=pane, tab=tab)
        exit_code = _pane_exit_code(pane)
        category = _pane_category(agent_status=agent_status, exit_code=exit_code)
        matched = _pane_matches_criterion(
            category=category,
            agent_status=agent_status,
            exit_code=exit_code,
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
                window_index=_tab_index(tab) if tab is not None else tab_id or "?",
                window_name=_tab_name(tab) if tab is not None else "tab",
                pane_index=_entry_text(pane, "pane_id") or _entry_text(pane, "terminal_id") or "?",
                process_name=_pane_process_name(pane),
                status_text=_pane_status_text(
                    agent_status=agent_status,
                    category=category,
                    exit_code=exit_code,
                ),
                cwd=_entry_text(pane, "foreground_cwd") or _entry_text(pane, "cwd") or "—",
                is_active=bool(pane.get("focused")),
                category=category,
                exit_code=exit_code,
                matched=matched,
            )
        )

    total_targets = len(pane_states)
    matched_targets = sum(1 for pane in pane_states if pane.matched)
    return TraceSnapshot(
        session_name=session_name,
        session_exists=True,
        total_windows=len(tabs),
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
