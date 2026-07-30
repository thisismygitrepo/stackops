import json
from collections.abc import Callable
from subprocess import CompletedProcess
from typing import cast

from stackops.scripts.python.helpers.helpers_sessions._tmux_process_inspection import (
    collect_active_pane_processes,
    is_shell_process,
)
from stackops.scripts.python.helpers.helpers_sessions.kill_models import KilledTarget


type JsonObject = dict[str, object]
type RunCommand = Callable[[list[str]], CompletedProcess[str]]
type Quote = Callable[[str], str]


def _required_object(value: object, context: str) -> JsonObject:
    if not isinstance(value, dict):
        raise ValueError(f"Herdr returned invalid {context}; expected an object.")
    return cast(JsonObject, value)


def _required_entries(mapping: JsonObject, key: str, context: str) -> list[JsonObject]:
    value = mapping.get(key)
    if not isinstance(value, list):
        raise ValueError(f"Herdr returned invalid {context}.{key}; expected an array.")
    entries: list[JsonObject] = []
    for index, entry in enumerate(value):
        entries.append(_required_object(entry, f"{context}.{key}[{index}]"))
    return entries


def _required_string(mapping: JsonObject, key: str, context: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or value == "":
        raise ValueError(f"Herdr returned invalid {context}.{key}; expected a non-empty string.")
    return value


def _run_json_command(args: list[str], run_command_fn: RunCommand) -> JsonObject:
    result = run_command_fn(args)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "command failed"
        raise ValueError(f"Unable to inspect Herdr state: {detail}")
    try:
        parsed: object = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise ValueError("Herdr returned invalid JSON while inspecting idle panes.") from error
    return _required_object(parsed, "response")


def _response_result(payload: JsonObject, expected_type: str) -> JsonObject:
    result = _required_object(payload.get("result"), "response.result")
    response_type = _required_string(result, "type", "response.result")
    if response_type != expected_type:
        raise ValueError(f"Herdr returned response type '{response_type}'; expected '{expected_type}'.")
    return result


def _session_snapshot(
    session_name: str,
    run_command_fn: RunCommand,
) -> tuple[dict[str, str], dict[str, list[str]], set[str]]:
    payload = _run_json_command(["herdr", "--session", session_name, "api", "snapshot"], run_command_fn)
    result = _response_result(payload, "session_snapshot")
    snapshot = _required_object(result.get("snapshot"), "response.result.snapshot")
    workspace_labels: dict[str, str] = {}
    pane_ids_by_workspace: dict[str, list[str]] = {}
    for workspace in _required_entries(snapshot, "workspaces", "snapshot"):
        workspace_id = _required_string(workspace, "workspace_id", "workspace")
        label = workspace.get("label")
        if not isinstance(label, str):
            raise ValueError("Herdr returned invalid workspace.label; expected a string.")
        workspace_labels[workspace_id] = label or workspace_id
        pane_ids_by_workspace[workspace_id] = []

    known_pane_ids: set[str] = set()
    for pane in _required_entries(snapshot, "panes", "snapshot"):
        pane_id = _required_string(pane, "pane_id", "pane")
        workspace_id = _required_string(pane, "workspace_id", "pane")
        workspace_panes = pane_ids_by_workspace.get(workspace_id)
        if workspace_panes is None:
            raise ValueError(f"Herdr pane '{pane_id}' references unknown workspace '{workspace_id}'.")
        workspace_panes.append(pane_id)
        known_pane_ids.add(pane_id)

    agent_pane_ids: set[str] = set()
    for agent in _required_entries(snapshot, "agents", "snapshot"):
        pane_id = _required_string(agent, "pane_id", "agent")
        if pane_id not in known_pane_ids:
            raise ValueError(f"Herdr agent references unknown pane '{pane_id}'.")
        agent_pane_ids.add(pane_id)
    return workspace_labels, pane_ids_by_workspace, agent_pane_ids


def _pane_is_idle(session_name: str, pane_id: str, run_command_fn: RunCommand) -> bool:
    payload = _run_json_command(
        ["herdr", "--session", session_name, "pane", "process-info", "--pane", pane_id],
        run_command_fn,
    )
    result = _response_result(payload, "pane_process_info")
    process_info = _required_object(result.get("process_info"), "response.result.process_info")
    returned_pane_id = _required_string(process_info, "pane_id", "process_info")
    if returned_pane_id != pane_id:
        raise ValueError(f"Herdr returned process information for pane '{returned_pane_id}', not '{pane_id}'.")
    shell_pid = process_info.get("shell_pid")
    if shell_pid is None:
        return False
    if isinstance(shell_pid, bool) or not isinstance(shell_pid, int):
        raise ValueError("Herdr returned invalid process_info.shell_pid; expected an integer or null.")
    foreground_processes = _required_entries(process_info, "foreground_processes", "process_info")
    if len(foreground_processes) != 1 or foreground_processes[0].get("pid") != shell_pid:
        return False
    descendants = [
        process
        for process in collect_active_pane_processes(pane_pid=str(shell_pid))
        if process.depth > 0
    ]
    return not any(not is_shell_process(process) or len(process.argv) > 1 for process in descendants)


def build_idle_kill_script_for_sessions(
    session_names: list[str],
    run_command_fn: RunCommand,
    quote_fn: Quote,
) -> tuple[str, list[KilledTarget]]:
    commands: list[str] = []
    killed_targets: list[KilledTarget] = []
    for session_name in session_names:
        workspace_labels, pane_ids_by_workspace, agent_pane_ids = _session_snapshot(session_name, run_command_fn)
        idle_pane_ids: set[str] = set()
        for pane_ids in pane_ids_by_workspace.values():
            for pane_id in pane_ids:
                if pane_id not in agent_pane_ids and _pane_is_idle(session_name, pane_id, run_command_fn):
                    idle_pane_ids.add(pane_id)

        idle_workspace_ids = [
            workspace_id
            for workspace_id, pane_ids in pane_ids_by_workspace.items()
            if all(pane_id in idle_pane_ids for pane_id in pane_ids)
        ]
        if len(idle_workspace_ids) == len(workspace_labels):
            commands.append(f"herdr session stop {quote_fn(session_name)} --json")
            killed_targets.append(KilledTarget(
                action="session",
                session=session_name,
                window="-",
                detail=f"{len(workspace_labels)} idle workspace(s)",
            ))
            continue

        for workspace_id, pane_ids in pane_ids_by_workspace.items():
            workspace_label = workspace_labels[workspace_id]
            if workspace_id in idle_workspace_ids:
                commands.append(
                    f"herdr --session {quote_fn(session_name)} workspace close {quote_fn(workspace_id)}"
                )
                killed_targets.append(KilledTarget(
                    action="window",
                    session=session_name,
                    window=workspace_label,
                    detail=f"{len(pane_ids)} idle pane(s)",
                ))
                continue
            for pane_id in pane_ids:
                if pane_id not in idle_pane_ids:
                    continue
                commands.append(
                    f"herdr --session {quote_fn(session_name)} pane close {quote_fn(pane_id)}"
                )
                killed_targets.append(KilledTarget(
                    action="pane",
                    session=session_name,
                    window=workspace_label,
                    detail=pane_id,
                ))
    return "\n".join(commands), killed_targets
