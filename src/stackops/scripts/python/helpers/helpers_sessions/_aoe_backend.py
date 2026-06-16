import json
from collections.abc import Iterable
from typing import Any, cast

from stackops.scripts.python.helpers.helpers_sessions._attach_common import (
    AttachSessionChoice,
    collect_selected_option_scripts,
    interactive_choose_with_preview,
    natural_sort_key,
    quote,
    run_command,
)
from stackops.scripts.python.helpers.helpers_sessions.kill_impl import KilledTarget


JsonObject = dict[str, Any]


def _run_json_command(args: list[str]) -> JsonObject | list[JsonObject] | None:
    try:
        result = run_command(args)
    except FileNotFoundError:
        return None
    if result.returncode != 0:
        return None

    text = result.stdout.strip()
    if text == "" or text.startswith("No sessions found"):
        return []

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, dict):
        return cast(JsonObject, parsed)
    if isinstance(parsed, list):
        return [cast(JsonObject, item) for item in parsed if isinstance(item, dict)]
    return None


def _dict_entries(value: object) -> list[JsonObject]:
    if not isinstance(value, list):
        return []
    return [cast(JsonObject, item) for item in value if isinstance(item, dict)]


def _session_entries_from_payload(payload: JsonObject | list[JsonObject] | None) -> list[JsonObject] | None:
    if payload is None:
        return None
    if isinstance(payload, list):
        return payload

    for key in ("sessions", "items", "data"):
        entries = _dict_entries(payload.get(key))
        if entries:
            return entries

    result = payload.get("result")
    if isinstance(result, dict):
        for key in ("sessions", "items", "data"):
            entries = _dict_entries(result.get(key))
            if entries:
                return entries

    return []


def _session_entries() -> list[JsonObject] | None:
    sessions = _session_entries_from_payload(_run_json_command(["aoe", "list", "--json"]))
    if sessions is None:
        return None
    sessions.sort(key=lambda session: natural_sort_key(_session_display_name(session)))
    return sessions


def _entry_text(entry: JsonObject, *keys: str) -> str | None:
    for key in keys:
        value = entry.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _session_title(session: JsonObject) -> str | None:
    return _entry_text(session, "title", "name")


def _session_id(session: JsonObject) -> str | None:
    return _entry_text(session, "id", "session_id", "sessionId")


def _session_identifier(session: JsonObject) -> str | None:
    return _session_title(session) or _session_id(session)


def _session_display_name(session: JsonObject) -> str:
    return _session_identifier(session) or "session"


def _session_status(session: JsonObject) -> str | None:
    return _entry_text(session, "status", "state", "run_status", "runStatus")


def _session_is_killable(session: JsonObject) -> bool:
    running = session.get("running")
    if isinstance(running, bool):
        return running

    status = (_session_status(session) or "").strip().lower().replace("_", " ")
    if status in {"stopped", "not started", "archived", "snoozed"}:
        return False
    return True


def _session_preview(session: JsonObject) -> str:
    lines = [
        "backend: aoe",
        f"session: {_session_title(session) or ''}",
        f"id: {_session_id(session) or ''}",
    ]
    status = _session_status(session)
    if status is not None:
        lines.append(f"status: {status}")
    group = _entry_text(session, "group", "group_path", "groupPath")
    if group is not None:
        lines.append(f"group: {group}")
    path = _entry_text(session, "path", "project_path", "projectPath", "workspace", "cwd")
    if path is not None:
        lines.append(f"path: {path}")
    agent = _entry_text(session, "agent", "tool", "command")
    if agent is not None:
        lines.append(f"agent: {agent}")
    return "\n".join(lines)


def _build_option_maps(sessions: Iterable[JsonObject]) -> tuple[dict[str, str], dict[str, str]]:
    options_to_script: dict[str, str] = {}
    options_to_preview_mapping: dict[str, str] = {}
    seen_labels: dict[str, int] = {}

    for session in sessions:
        identifier = _session_identifier(session)
        if identifier is None:
            continue
        label = _session_display_name(session)
        seen = seen_labels.get(label, 0)
        seen_labels[label] = seen + 1
        if seen:
            label = f"{label} ({_session_id(session) or seen + 1})"
        options_to_script[label] = identifier
        options_to_preview_mapping[label] = _session_preview(session)
    return options_to_script, options_to_preview_mapping


def attach_script_from_name(name: str) -> str:
    return f"aoe session attach {quote(name)}"


def stop_session_script(name: str) -> str:
    return f"aoe session stop {quote(name)}"


def choose_session(
    name: str | None,
    new_session: bool,
    kill_all: bool,
    window: bool = False,
) -> AttachSessionChoice:
    if name is not None:
        return ("handoff_script", attach_script_from_name(name))
    if new_session:
        return ("error", "AoE backend cannot create an empty session. Use `terminal run-aoe` to add sessions from a layout.")
    if kill_all:
        return ("error", "AoE backend does not support --kill-all while attaching.")
    if window:
        return ("error", "AoE backend only supports session-level attach.")

    sessions = _session_entries()
    if sessions is None:
        return ("error", "Could not read AoE sessions. Is `aoe` installed?")
    if len(sessions) == 0:
        return ("error", "No AoE sessions are available to attach to.")

    option_to_identifier, options_to_preview_mapping = _build_option_maps(sessions)
    selection = interactive_choose_with_preview(
        msg="Choose an AoE session to attach to:",
        options_to_preview_mapping=options_to_preview_mapping,
    )
    if selection is None:
        return ("error", "No AoE session selected.")
    identifier = option_to_identifier.get(selection)
    if identifier is None:
        return ("error", f"Unknown AoE session selected: {selection}")
    return ("handoff_script", attach_script_from_name(identifier))


def choose_kill_target(
    name: str | None,
    kill_all: bool,
    idle: bool,
    window: bool,
) -> tuple[str, str | None, list[KilledTarget]]:
    if idle:
        return ("error", "AoE backend does not support --idle.", [])
    if window:
        return ("error", "AoE backend only supports session-level kill.", [])
    if name is not None:
        return (
            "run_script",
            stop_session_script(name),
            [{"action": "session", "session": name, "window": "-", "detail": "-"}],
        )

    sessions = _session_entries()
    if sessions is None:
        return ("error", "Could not read AoE sessions. Is `aoe` installed?", [])

    killable_sessions = [session for session in sessions if _session_is_killable(session)]
    if len(killable_sessions) == 0:
        return ("error", "No running AoE sessions are available to kill.", [])

    option_to_identifier, options_to_preview_mapping = _build_option_maps(killable_sessions)

    if kill_all:
        identifiers = list(option_to_identifier.values())
        killed_targets: list[KilledTarget] = [
            {"action": "session", "session": identifier, "window": "-", "detail": "-"}
            for identifier in identifiers
        ]
        return ("run_script", "\n".join(stop_session_script(identifier) for identifier in identifiers), killed_targets)

    selections = interactive_choose_with_preview(
        msg="Choose an AoE session to kill:",
        options_to_preview_mapping=options_to_preview_mapping,
        multi=True,
    )
    if len(selections) == 0:
        return ("error", "No AoE session selected.", [])
    option_to_script = {
        label: stop_session_script(identifier)
        for label, identifier in option_to_identifier.items()
    }
    scripts, unknown_selection = collect_selected_option_scripts(
        selections=selections,
        options_to_script=option_to_script,
        option_parent_labels={},
    )
    if unknown_selection is not None:
        return ("error", f"Unknown AoE session selected: {unknown_selection}", [])
    killed_targets = [
        {"action": "session", "session": option_to_identifier[selection], "window": "-", "detail": "-"}
        for selection in dict.fromkeys(selections)
        if selection in option_to_identifier
    ]
    return ("run_script", "\n".join(scripts), killed_targets)
