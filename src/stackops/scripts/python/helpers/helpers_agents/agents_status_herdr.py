import json
from concurrent.futures import ThreadPoolExecutor
from subprocess import TimeoutExpired
from typing import cast

from stackops.scripts.python.helpers.helpers_agents.agents_status_models import JsonObject, StatusOptions
from stackops.scripts.python.helpers.helpers_agents.agents_status_tuios import json_object, text_field
from stackops.scripts.python.helpers.helpers_sessions._attach_common import run_command


def query_herdr(*, options: StatusOptions, session: str | None, arguments: list[str]) -> tuple[object, str | None]:
    if tuple(arguments[:2]) not in {
        ("session", "list"), ("api", "snapshot"), ("pane", "list"),
        ("pane", "process-info"), ("pane", "read"), ("agent", "explain"), ("agent", "get"),
    }:
        raise ValueError("agents status only permits read-only Herdr inspection commands.")
    command = ["herdr", *(["--session", session] if session is not None else []), *arguments]
    operation = " ".join(arguments[:2])
    try:
        result = run_command(command, timeout=options.timeout)
    except (OSError, TimeoutExpired) as error:
        return None, f"""{operation}: {error}"""
    if result.returncode != 0:
        return None, f"""{operation} exited {result.returncode}: {result.stderr.strip() or result.stdout.strip()}"""
    try:
        payload: object = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        return None, f"""{operation} returned invalid JSON: {error}"""
    if not isinstance(payload, dict):
        return None, f"""{operation} returned a non-object JSON response."""
    if payload.get("error") is not None:
        return None, f"""{operation}: {payload['error']}"""
    return payload, None


def _entries(*, payload: JsonObject, key: str) -> list[JsonObject]:
    value = payload.get(key)
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise ValueError(f"""Herdr returned an invalid {key} list.""")
    return cast(list[JsonObject], value)


def read_herdr_inventory(*, options: StatusOptions) -> tuple[list[JsonObject], list[JsonObject], list[JsonObject], list[str]]:
    payload, error = query_herdr(options=options, session=None, arguments=["session", "list", "--json"])
    if error is not None:
        raise ValueError(error)
    sessions: list[JsonObject] = []
    for entry in _entries(payload=json_object(payload), key="sessions"):
        name = text_field(entry, ("name",))
        if not name or not isinstance(entry.get("running"), bool):
            raise ValueError("Herdr returned a session without a valid name and running state.")
        sessions.append({**entry, "name": name, "id": name, "saved": not entry["running"], "workspaces": [], "window_count": 0})
    selected_sessions = [
        session for session in sessions
        if not session["saved"] and (not options.sessions or session["name"] in options.sessions)
    ]
    with ThreadPoolExecutor(max_workers=options.workers) as executor:
        snapshots = list(executor.map(
            lambda session: query_herdr(options=options, session=text_field(session, ("name",)), arguments=["api", "snapshot"]),
            selected_sessions,
        ))
    panes: list[JsonObject] = []
    registrations: list[JsonObject] = []
    for session, (snapshot_payload, snapshot_error) in zip(selected_sessions, snapshots, strict=True):
        name = text_field(session, ("name",))
        if snapshot_error is not None:
            raise ValueError(f"""Herdr session {name}: {snapshot_error}""")
        result = json_object(json_object(snapshot_payload).get("result"))
        snapshot = json_object(result.get("snapshot"))
        workspaces = _entries(payload=snapshot, key="workspaces")
        tabs = _entries(payload=snapshot, key="tabs")
        session_panes = _entries(payload=snapshot, key="panes")
        agents = _entries(payload=snapshot, key="agents")
        workspace_by_id = {text_field(workspace, ("workspace_id",)): workspace for workspace in workspaces}
        tab_by_id = {text_field(tab, ("tab_id",)): tab for tab in tabs}
        agent_by_pane = {text_field(agent, ("pane_id",)): agent for agent in agents}
        session["workspaces"] = workspaces
        session["window_count"] = len(session_panes)
        for pane in session_panes:
            pane_id = text_field(pane, ("pane_id",))
            workspace = workspace_by_id.get(text_field(pane, ("workspace_id",)), {})
            tab = tab_by_id.get(text_field(pane, ("tab_id",)), {})
            agent = agent_by_pane.get(pane_id, {})
            panes.append({
                **pane, "session": name, "window_id": pane_id,
                "name": text_field(agent, ("name",)) or text_field(pane, ("label", "title")),
                "workspace": workspace.get("number"), "workspace_name": text_field(workspace, ("label",)),
                "tab_name": text_field(tab, ("label",)),
            })
        registrations.extend({**agent, "session": name, "window_id": text_field(agent, ("pane_id",))} for agent in agents)
    return sessions, panes, registrations, []


def read_herdr_panes(*, options: StatusOptions, sessions: tuple[str, ...]) -> tuple[list[JsonObject], str | None]:
    with ThreadPoolExecutor(max_workers=options.workers) as executor:
        results = list(executor.map(
            lambda session: query_herdr(options=options, session=session, arguments=["pane", "list"]), sessions,
        ))
    panes: list[JsonObject] = []
    errors: list[str] = []
    for session, (payload, error) in zip(sessions, results, strict=True):
        if error is not None:
            errors.append(f"""Session {session}: {error}""")
            continue
        try:
            entries = _entries(payload=json_object(json_object(payload).get("result")), key="panes")
        except ValueError as invalid_response:
            errors.append(f"""Session {session}: {invalid_response}""")
            continue
        panes.extend({
            **pane, "session": session, "window_id": text_field(pane, ("pane_id",)),
            "name": text_field(pane, ("label", "title")),
        } for pane in entries)
    return panes, "; ".join(errors) if errors else None
