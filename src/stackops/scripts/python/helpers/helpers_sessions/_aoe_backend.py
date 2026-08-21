import json
from collections.abc import Iterable
from typing import cast

from stackops.scripts.python.helpers.helpers_sessions._attach_common import (
    AttachSessionChoice,
    collect_selected_option_scripts,
    interactive_choose_with_preview,
    natural_sort_key,
    quote,
    run_command,
)
from stackops.scripts.python.helpers.helpers_sessions.kill_models import KilledTarget


type JsonObject = dict[str, object]


def _run_json_command(args: list[str]) -> list[JsonObject] | None:
    try:
        result = run_command(args)
    except FileNotFoundError:
        return None
    if result.returncode != 0:
        return None

    text = result.stdout.strip()
    if text.startswith("No sessions found"):
        return []
    if text == "":
        return None

    try:
        parsed = cast(object, json.loads(text))
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, list):
        return None
    entries: list[JsonObject] = []
    for item in parsed:
        if not isinstance(item, dict):
            return None
        entries.append(cast(JsonObject, item))
    return entries


def _entry_text(entry: JsonObject, *keys: str) -> str | None:
    for key in keys:
        value = entry.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _session_entries() -> list[JsonObject] | None:
    sessions = _run_json_command(["aoe", "list", "--json"])
    if sessions is None:
        return None
    if len(sessions) == 0:
        return []

    runtime_entries = _run_json_command(["aoe", "ps", "--tmux", "--json", "--dead"])
    if runtime_entries is None:
        return None
    runtime_by_session_id: dict[str, JsonObject] = {}
    for runtime_entry in runtime_entries:
        session_id = _entry_text(runtime_entry, "session")
        if session_id is None or session_id in runtime_by_session_id:
            return None
        runtime_by_session_id[session_id] = runtime_entry

    terminal_sessions: list[JsonObject] = []
    for session in sessions:
        session_id = _entry_text(session, "id")
        if session_id is None:
            return None
        runtime_entry = runtime_by_session_id.get(session_id)
        if runtime_entry is None:
            continue
        state = _entry_text(runtime_entry, "state")
        if state is None:
            return None
        merged_session = session | runtime_entry
        merged_session["running"] = state != "dead"
        terminal_sessions.append(merged_session)

    terminal_sessions.sort(key=lambda session: natural_sort_key(_session_display_name(session)))
    return terminal_sessions


def list_session_entries() -> list[JsonObject] | None:
    return _session_entries()


def entry_text(entry: JsonObject, *keys: str) -> str | None:
    return _entry_text(entry, *keys)


def _session_title(session: JsonObject) -> str | None:
    return _entry_text(session, "title")


def session_title(session: JsonObject) -> str | None:
    return _session_title(session)


def _session_id(session: JsonObject) -> str | None:
    return _entry_text(session, "id")


def session_id(session: JsonObject) -> str | None:
    return _session_id(session)


def _session_identifier(session: JsonObject) -> str | None:
    return _session_id(session) or _session_title(session)


def session_identifier(session: JsonObject) -> str | None:
    return _session_identifier(session)


def _session_display_name(session: JsonObject) -> str:
    return _session_title(session) or _session_id(session) or "session"


def session_display_name(session: JsonObject) -> str:
    return _session_display_name(session)


def _session_status(session: JsonObject) -> str | None:
    return _entry_text(session, "state")


def session_status(session: JsonObject) -> str | None:
    return _session_status(session)


def _session_is_killable(session: JsonObject) -> bool:
    return session.get("running") is True


def list_killable_session_names() -> list[str] | None:
    sessions = _session_entries()
    if sessions is None:
        return None
    return [
        identifier
        for session in sessions
        if _session_is_killable(session)
        if (identifier := _session_identifier(session)) is not None
    ]


def session_preview(session: JsonObject) -> str:
    lines = [
        "backend: aoe",
        f"session: {_session_title(session) or ''}",
        f"id: {_session_id(session) or ''}",
    ]
    status = _session_status(session)
    if status is not None:
        lines.append(f"status: {status}")
    group = _entry_text(session, "group")
    if group is not None:
        lines.append(f"group: {group}")
    path = _entry_text(session, "path")
    if path is not None:
        lines.append(f"path: {path}")
    agent = _entry_text(session, "agent", "tool")
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
        options_to_preview_mapping[label] = session_preview(session)
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
        return ("error", "AoE backend cannot create an empty session. Use `terminal run --backend aoe` to add sessions from a layout.")
    if kill_all:
        return ("error", "AoE backend does not support --kill-all while attaching.")
    if window:
        return ("error", "AoE backend only supports session-level attach.")

    sessions = _session_entries()
    if sessions is None:
        return ("error", "Could not read AoE sessions. Is `aoe` installed?")
    running_sessions = [session for session in sessions if _session_is_killable(session)]
    if len(running_sessions) == 0:
        return ("error", "No running AoE sessions are available to attach to.")

    option_to_identifier, options_to_preview_mapping = _build_option_maps(running_sessions)
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
