import json
from subprocess import TimeoutExpired
from typing import cast

from stackops.scripts.python.helpers.helpers_agents.agents_status_models import JsonObject, StatusOptions
from stackops.scripts.python.helpers.helpers_agents.agents_status_tuios import text_field
from stackops.scripts.python.helpers.helpers_sessions._attach_common import run_command


def query_aoe(*, options: StatusOptions, arguments: list[str]) -> tuple[object, str | None]:
    if not arguments or not (
        arguments[0] in {"list", "ps"}
        or tuple(arguments[:2]) in {("session", "capture"), ("acp", "status"), ("acp", "history")}
    ):
        raise ValueError("agents status only permits AoE inspection commands.")
    operation = " ".join(arguments[:2])
    try:
        result = run_command(["aoe", *arguments], timeout=options.timeout)
    except (OSError, TimeoutExpired) as error:
        return None, f"""{operation}: {error}"""
    if result.returncode != 0:
        return None, f"""{operation} exited {result.returncode}: {result.stderr.strip() or result.stdout.strip()}"""
    output = result.stdout.strip()
    if arguments[0] in {"list", "ps"} and output.startswith("No sessions found"):
        return [], None
    try:
        if arguments[:2] == ["acp", "history"]:
            return [json.loads(line) for line in output.splitlines() if line.strip()], None
        payload: object = json.loads(output)
    except json.JSONDecodeError as error:
        return None, f"""{operation} returned invalid JSON: {error}"""
    return payload, None


def _entries(*, payload: object, operation: str) -> list[JsonObject]:
    if not isinstance(payload, list) or any(not isinstance(row, dict) for row in payload):
        raise ValueError(f"""AoE {operation} returned an invalid session list.""")
    return cast(list[JsonObject], payload)


def read_aoe_inventory(*, options: StatusOptions) -> tuple[list[JsonObject], list[JsonObject], list[JsonObject], list[str]]:
    payload, error = query_aoe(options=options, arguments=["list", "--json"])
    if error is not None:
        raise ValueError(error)
    entries = _entries(payload=payload, operation="list")
    if not entries:
        return [], [], [], []
    profiles = {text_field(entry, ("profile",)) for entry in entries}
    if len(profiles) != 1 or "" in profiles:
        raise ValueError("AoE list did not identify one current profile.")
    profile = next(iter(profiles))
    runtime_payload, runtime_error = query_aoe(options=options, arguments=["ps", "--json", "--dead", "--profile", profile])
    if runtime_error is not None:
        raise ValueError(runtime_error)
    runtimes = _entries(payload=runtime_payload, operation="ps")
    runtimes_by_id: dict[str, JsonObject] = {}
    for runtime in runtimes:
        session_id = text_field(runtime, ("session",))
        if not session_id or runtime.get("substrate") not in {"tmux", "acp"} or not text_field(runtime, ("state",)):
            raise ValueError("AoE returned a runtime without a valid session, substrate or state.")
        previous = runtimes_by_id.get(session_id)
        if previous is not None and previous.get("state") != "dead" and runtime.get("state") != "dead":
            raise ValueError(f"""AoE session {session_id} has multiple live runtimes; its agent identity is ambiguous.""")
        if previous is None or previous.get("state") == "dead":
            runtimes_by_id[session_id] = runtime
    title_counts: dict[str, int] = {}
    for entry in entries:
        title = text_field(entry, ("title", "id"))
        title_counts[title] = title_counts.get(title, 0) + 1
    sessions: list[JsonObject] = []
    panes: list[JsonObject] = []
    known_ids: set[str] = set()
    for entry in entries:
        session_id = text_field(entry, ("id",))
        if not session_id or session_id in known_ids:
            raise ValueError("AoE returned a missing or duplicate session ID.")
        known_ids.add(session_id)
        title = text_field(entry, ("title",)) or session_id
        name = f"""{title} ({session_id})""" if title_counts[title] > 1 else title
        runtime = runtimes_by_id.get(session_id)
        running = runtime is not None and runtime.get("state") != "dead"
        session: JsonObject = {**entry, "name": name, "id": session_id, "saved": not running, "workspaces": [], "window_count": int(running)}
        sessions.append(session)
        if not running or runtime is None or options.sessions and not {name, title, session_id}.intersection(options.sessions):
            continue
        panes.append({
            **entry, **runtime, "session": name, "window_id": session_id, "name": title,
            "workspace": None, "workspace_name": text_field(entry, ("group",)),
        })
    limitations = []
    if any(text_field(runtime, ("session",)) not in known_ids for runtime in runtimes):
        limitations.append("AoE runtime entries without matching current-profile session metadata were not inspected.")
    return sessions, panes, list(panes), limitations


def read_aoe_panes(*, options: StatusOptions, sessions: tuple[JsonObject, ...]) -> tuple[list[JsonObject], str | None]:
    if not sessions:
        return [], None
    profile = text_field(sessions[0], ("profile",))
    payload, error = query_aoe(options=options, arguments=["ps", "--json", "--dead", "--profile", profile])
    if error is not None:
        return [], error
    try:
        runtimes = _entries(payload=payload, operation="ps")
    except ValueError as invalid_response:
        return [], str(invalid_response)
    live_ids = {text_field(runtime, ("session",)) for runtime in runtimes if runtime.get("state") != "dead"}
    panes: list[JsonObject] = []
    for session in sessions:
        session_id = text_field(session, ("id",))
        if session_id in live_ids:
            panes.append({"session": session["name"], "window_id": session_id, "name": text_field(session, ("title", "name"))})
    return panes, None
