import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from subprocess import TimeoutExpired
from typing import cast

import psutil

from stackops.scripts.python.helpers.helpers_agents.agents_status_models import JsonObject, StatusOptions
from stackops.scripts.python.helpers.helpers_sessions._attach_common import run_command


def query_tuios(*, options: StatusOptions, arguments: list[str]) -> tuple[object, str | None]:
    if arguments[0] not in {
        "ls", "list-agents", "list-windows", "list-workspaces", "get-window", "explain-agent-detect",
        "agent-log", "get-agent-state", "peek-prompt", "capture-pane",
    }:
        raise ValueError("agents status only permits read-only TUIOS inspection commands.")
    command = ["tuios", *arguments]
    if options.server is not None:
        command.extend(["--server", options.server])
    try:
        result = run_command(command, timeout=options.timeout)
    except (OSError, TimeoutExpired) as error:
        return None, f"""{arguments[0]}: {error}"""
    if result.returncode != 0 and not (arguments[0] == "ls" and result.returncode == 3):
        return None, f"""{arguments[0]} exited {result.returncode}: {result.stderr.strip() or result.stdout.strip()}"""
    try:
        payload: object = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        return None, f"""{arguments[0]} returned invalid JSON: {error}"""
    if isinstance(payload, dict) and payload.get("success") is False:
        return None, f"""{arguments[0]}: {payload.get('error') or payload.get('message') or 'inspection failed'}"""
    return payload, None


def object_rows(*, payload: object, key: str | None) -> list[JsonObject]:
    if key is not None and (not isinstance(payload, dict) or key not in payload):
        raise ValueError(f"""TUIOS response has no {key} list.""")
    value = payload.get(key) if isinstance(payload, dict) and key is not None else payload
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise ValueError(f"""TUIOS returned an invalid {key or 'session'} list.""")
    return cast(list[JsonObject], value)


def json_object(payload: object) -> JsonObject:
    if not isinstance(payload, dict):
        return {}
    return cast(JsonObject, payload)


def text_field(row: JsonObject, keys: tuple[str, ...]) -> str:
    for key in keys:
        value = row.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def observer_ancestors() -> tuple[set[int], str | None]:
    try:
        return {process.pid for process in psutil.Process().parents()}, None
    except (psutil.Error, OSError) as error:
        return set(), f"""Observer process ancestry unavailable: {error}"""


def read_inventory(*, options: StatusOptions) -> tuple[list[JsonObject], list[JsonObject], list[JsonObject], list[str]]:
    queries = [
        ["ls", "--json"],
        ["list-agents", "--all-sessions", "--json"],
        ["list-windows", "--all", "--text", "20", "--json"],
    ]
    with ThreadPoolExecutor(max_workers=options.workers) as executor:
        results = list(executor.map(lambda args: query_tuios(options=options, arguments=args), queries))
    sessions_payload, sessions_error = results[0]
    if sessions_error is not None:
        raise ValueError(sessions_error)
    sessions = object_rows(payload=sessions_payload, key=None)
    if not any(not session.get("saved") for session in sessions):
        return sessions, [], [], []
    panes_payload, panes_error = results[2]
    if panes_error is not None:
        raise ValueError(panes_error)
    panes = object_rows(payload=panes_payload, key="panes")
    agents_payload, agents_error = results[1]
    agents = object_rows(payload=agents_payload, key="agents") if agents_error is None else []
    return sessions, panes, agents, [agents_error] if agents_error is not None else []


def validate_history_roots(*, options: StatusOptions) -> None:
    private_root = Path.home().joinpath("dotfiles")
    for path in (options.claude_home, options.codex_home):
        if path.expanduser().absolute().is_relative_to(private_root) or path.expanduser().resolve().is_relative_to(private_root):
            raise ValueError("Agent history directories under ~/dotfiles cannot be inspected.")
