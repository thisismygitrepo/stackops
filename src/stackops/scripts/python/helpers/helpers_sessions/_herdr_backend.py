import json
import uuid
from collections.abc import Iterable
from datetime import datetime
from typing import Any, cast

from stackops.scripts.python.helpers.helpers_sessions.attach_impl import (
    AttachSessionChoice,
    KILL_ALL_AND_NEW_LABEL,
    NEW_SESSION_LABEL,
    interactive_choose_with_preview,
    natural_sort_key,
    quote,
    run_command,
)


JsonObject = dict[str, Any]


def _run_json_command(args: list[str]) -> JsonObject | None:
    try:
        result = run_command(args)
    except FileNotFoundError:
        return None
    if result.returncode != 0:
        return None
    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    return cast(JsonObject, parsed)


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


def _session_entries() -> list[JsonObject] | None:
    payload = _run_json_command(["herdr", "session", "list", "--json"])
    if payload is None:
        return None
    sessions = _dict_entries(payload.get("sessions"))
    sessions.sort(
        key=lambda session: (
            not bool(session.get("default")),
            not bool(session.get("running")),
            natural_sort_key(str(session.get("name") or "")),
        )
    )
    return sessions


def _session_name(session: JsonObject) -> str | None:
    name = session.get("name")
    if isinstance(name, str) and name:
        return name
    return None


def _running_session_names(sessions: Iterable[JsonObject]) -> list[str]:
    names: list[str] = []
    for session in sessions:
        name = _session_name(session)
        if name is not None and bool(session.get("running")):
            names.append(name)
    return names


def _new_session_name() -> str:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    suffix = uuid.uuid4().hex[:6]
    return f"stackops-{timestamp}-{suffix}"


def attach_script_from_name(name: str) -> str:
    return f"herdr session attach {quote(name)}"


def new_session_script(kill_all: bool, sessions: list[JsonObject] | None = None) -> str:
    session_name = _new_session_name()
    commands: list[str] = []
    if kill_all:
        session_entries = sessions if sessions is not None else _session_entries()
        for existing_name in _running_session_names(session_entries or []):
            commands.append(stop_session_script(existing_name))
    commands.append(f"herdr --session {quote(session_name)}")
    return "\n".join(commands)


def stop_session_script(name: str) -> str:
    return f"herdr session stop {quote(name)} --json"


def _tab_entries(session_name: str) -> list[JsonObject]:
    payload = _run_json_command(["herdr", "--session", session_name, "tab", "list"])
    return _result_entries(payload, "tabs")


def _pane_entries(session_name: str) -> list[JsonObject]:
    payload = _run_json_command(["herdr", "--session", session_name, "pane", "list"])
    return _result_entries(payload, "panes")


def _entry_text(entry: JsonObject, key: str) -> str | None:
    value = entry.get(key)
    if isinstance(value, str) and value:
        return value
    return None


def _tab_display(tab: JsonObject) -> str:
    tab_id = _entry_text(tab, "tab_id")
    label = _entry_text(tab, "label") or tab_id or "tab"
    number = tab.get("number")
    if isinstance(number, int):
        return f"{number}:{label}"
    return label


def _pane_display(pane: JsonObject, tab_display_by_id: dict[str, str]) -> str:
    label = (
        _entry_text(pane, "label")
        or _entry_text(pane, "agent")
        or _entry_text(pane, "terminal_id")
        or _entry_text(pane, "pane_id")
        or "pane"
    )
    tab_id = _entry_text(pane, "tab_id")
    if tab_id is not None:
        tab_display = tab_display_by_id.get(tab_id)
        if tab_display is not None:
            return f"{tab_display} / {label}"
    return label


def _tab_preview(session_name: str, tab: JsonObject) -> str:
    lines = [
        "backend: herdr",
        f"session: {session_name}",
        f"tab: {_tab_display(tab)}",
        f"id: {_entry_text(tab, 'tab_id') or ''}",
        f"focused: {'yes' if tab.get('focused') else 'no'}",
    ]
    agent_status = _entry_text(tab, "agent_status")
    if agent_status is not None:
        lines.append(f"agent status: {agent_status}")
    pane_count = tab.get("pane_count")
    if isinstance(pane_count, int):
        lines.append(f"panes: {pane_count}")
    return "\n".join(lines)


def _pane_preview(session_name: str, pane: JsonObject, tab_display_by_id: dict[str, str]) -> str:
    lines = [
        "backend: herdr",
        f"session: {session_name}",
        f"pane: {_pane_display(pane, tab_display_by_id)}",
        f"pane id: {_entry_text(pane, 'pane_id') or ''}",
        f"terminal id: {_entry_text(pane, 'terminal_id') or ''}",
        f"focused: {'yes' if pane.get('focused') else 'no'}",
    ]
    agent = _entry_text(pane, "agent")
    if agent is not None:
        lines.append(f"agent: {agent}")
    agent_status = _entry_text(pane, "agent_status")
    if agent_status is not None:
        lines.append(f"agent status: {agent_status}")
    cwd = _entry_text(pane, "foreground_cwd") or _entry_text(pane, "cwd")
    if cwd is not None:
        lines.append(f"cwd: {cwd}")
    return "\n".join(lines)


def _session_preview(session: JsonObject) -> str:
    name = _session_name(session) or ""
    lines = [
        "backend: herdr",
        f"session: {name}",
        f"default: {'yes' if session.get('default') else 'no'}",
        f"running: {'yes' if session.get('running') else 'no'}",
    ]
    session_dir = _entry_text(session, "session_dir")
    if session_dir is not None:
        lines.append(f"session dir: {session_dir}")
    socket_path = _entry_text(session, "socket_path")
    if socket_path is not None:
        lines.append(f"socket: {socket_path}")
    if bool(session.get("running")) and name:
        tabs = _tab_entries(name)
        panes = _pane_entries(name)
        lines.extend(["", f"tabs: {len(tabs)}", f"panes: {len(panes)}"])
    return "\n".join(lines)


def _attach_tab_script(session_name: str, tab_id: str) -> str:
    return "\n".join(
        [
            f"herdr --session {quote(session_name)} tab focus {quote(tab_id)}",
            attach_script_from_name(session_name),
        ]
    )


def _attach_pane_script(session_name: str, focus_target: str) -> str:
    return "\n".join(
        [
            f"herdr --session {quote(session_name)} agent focus {quote(focus_target)}",
            attach_script_from_name(session_name),
        ]
    )


def _close_tab_script(session_name: str, tab_id: str) -> str:
    return f"herdr --session {quote(session_name)} tab close {quote(tab_id)}"


def _close_pane_script(session_name: str, pane_id: str) -> str:
    return f"herdr --session {quote(session_name)} pane close {quote(pane_id)}"


def _build_window_target_options(
    active_sessions: list[str],
    *,
    for_kill: bool,
) -> tuple[dict[str, str], dict[str, str]]:
    options_to_script: dict[str, str] = {}
    options_to_preview: dict[str, str] = {}
    for session_name in active_sessions:
        tabs = _tab_entries(session_name)
        panes = _pane_entries(session_name)
        tab_display_by_id = {
            tab_id: _tab_display(tab)
            for tab in tabs
            if (tab_id := _entry_text(tab, "tab_id")) is not None
        }
        for tab in tabs:
            tab_id = _entry_text(tab, "tab_id")
            if tab_id is None:
                continue
            label = f"[{session_name}] {_tab_display(tab)}"
            if tab.get("focused"):
                label += " *"
            options_to_script[label] = (
                _close_tab_script(session_name, tab_id)
                if for_kill
                else _attach_tab_script(session_name, tab_id)
            )
            options_to_preview[label] = _tab_preview(session_name, tab)

        for pane in panes:
            pane_id = _entry_text(pane, "pane_id")
            terminal_id = _entry_text(pane, "terminal_id")
            target_id = pane_id if for_kill else terminal_id or pane_id
            if target_id is None:
                continue
            label = f"[{session_name}] {_pane_display(pane, tab_display_by_id)}"
            if pane.get("focused"):
                label += " *"
            options_to_script[label] = (
                _close_pane_script(session_name, target_id)
                if for_kill
                else _attach_pane_script(session_name, target_id)
            )
            options_to_preview[label] = _pane_preview(session_name, pane, tab_display_by_id)
    return (options_to_script, options_to_preview)


def choose_session(
    name: str | None,
    new_session: bool,
    kill_all: bool,
    window: bool = False,
) -> AttachSessionChoice:
    if name is not None:
        return ("handoff_script", attach_script_from_name(name))

    sessions = _session_entries()
    if sessions is None:
        return ("error", "Unable to list Herdr sessions. Confirm `herdr session list --json` works.")

    if new_session:
        return ("handoff_script", new_session_script(kill_all=kill_all, sessions=sessions))

    if len(sessions) == 0:
        return ("handoff_script", "herdr")

    if window:
        active_sessions = _running_session_names(sessions)
        if len(active_sessions) == 0:
            return ("error", "No running Herdr sessions are available for --window selection.")
        option_to_script, options_to_preview_mapping = _build_window_target_options(
            active_sessions,
            for_kill=False,
        )
        if len(option_to_script) == 0:
            return ("error", "No Herdr tabs or panes are available to attach to.")
        if len(option_to_script) == 1:
            return ("handoff_script", next(iter(option_to_script.values())))
        options_to_preview_mapping[NEW_SESSION_LABEL] = (
            "backend: herdr\naction: create a fresh named session\n\n"
            + new_session_script(kill_all=kill_all, sessions=sessions)
        )
        if not kill_all:
            options_to_preview_mapping[KILL_ALL_AND_NEW_LABEL] = (
                "backend: herdr\naction: stop every running session, then start a new one\n\n"
                + new_session_script(kill_all=True, sessions=sessions)
            )
        selection = interactive_choose_with_preview(
            msg="Choose a Herdr tab or pane to attach to:",
            options_to_preview_mapping=options_to_preview_mapping,
        )
        if selection is None:
            return ("error", "No Herdr tab or pane selected.")
        if selection == NEW_SESSION_LABEL:
            return ("handoff_script", new_session_script(kill_all=kill_all, sessions=sessions))
        if selection == KILL_ALL_AND_NEW_LABEL:
            return ("handoff_script", new_session_script(kill_all=True, sessions=sessions))
        script = option_to_script.get(selection)
        if script is None:
            return ("error", f"Unknown Herdr target selected: {selection}")
        return ("handoff_script", script)

    if len(sessions) == 1:
        session_name = _session_name(sessions[0])
        if session_name is None:
            return ("error", "Herdr session list did not include a usable session name.")
        return ("handoff_script", attach_script_from_name(session_name))

    display_to_session = {
        session_name: session
        for session in sessions
        if (session_name := _session_name(session)) is not None
    }
    options_to_preview_mapping = {
        session_name: _session_preview(session)
        for session_name, session in display_to_session.items()
    }
    options_to_preview_mapping[NEW_SESSION_LABEL] = (
        "backend: herdr\naction: create a fresh named session\n\n"
        + new_session_script(kill_all=kill_all, sessions=sessions)
    )
    if not kill_all:
        options_to_preview_mapping[KILL_ALL_AND_NEW_LABEL] = (
            "backend: herdr\naction: stop every running session, then start a new one\n\n"
            + new_session_script(kill_all=True, sessions=sessions)
        )
    session_label = interactive_choose_with_preview(
        msg="Choose a Herdr session to attach to:",
        options_to_preview_mapping=options_to_preview_mapping,
    )
    if session_label is None:
        return ("error", "No Herdr session selected.")
    if session_label == NEW_SESSION_LABEL:
        return ("handoff_script", new_session_script(kill_all=kill_all, sessions=sessions))
    if session_label == KILL_ALL_AND_NEW_LABEL:
        return ("handoff_script", new_session_script(kill_all=True, sessions=sessions))
    if session_label not in display_to_session:
        return ("error", f"Unknown Herdr session selected: {session_label}")
    return ("handoff_script", attach_script_from_name(session_label))


def choose_kill_target(
    name: str | None,
    kill_all: bool,
    idle: bool,
    window: bool,
) -> tuple[str, str | None]:
    if idle:
        return ("error", "--idle is only supported for the tmux backend because Herdr shell-idle status is not available.")
    sessions = _session_entries()
    if sessions is None:
        return ("error", "Unable to list Herdr sessions. Confirm `herdr session list --json` works.")

    if kill_all:
        scripts = [stop_session_script(session_name) for session_name in _running_session_names(sessions)]
        if len(scripts) == 0:
            return ("error", "No running Herdr sessions are available to kill.")
        return ("run_script", "\n".join(scripts))

    if name is not None:
        return ("run_script", stop_session_script(name))

    if len(sessions) == 0:
        return ("error", "No Herdr sessions are available to kill.")

    options_to_script: dict[str, str] = {}
    options_to_preview_mapping: dict[str, str] = {}

    if window:
        for session in sessions:
            session_name = _session_name(session)
            if session_name is None:
                continue
            session_label = f"[{session_name}] SESSION"
            if bool(session.get("default")):
                session_label += " (default)"
            if bool(session.get("running")):
                session_label += " (running)"
            options_to_script[session_label] = stop_session_script(session_name)
            options_to_preview_mapping[session_label] = _session_preview(session)
        active_sessions = _running_session_names(sessions)
        target_scripts, target_previews = _build_window_target_options(
            active_sessions,
            for_kill=True,
        )
        options_to_script.update(target_scripts)
        options_to_preview_mapping.update(target_previews)
        msg = "Choose a Herdr session, tab, or pane to kill:"
    else:
        for session in sessions:
            session_name = _session_name(session)
            if session_name is None:
                continue
            options_to_script[session_name] = stop_session_script(session_name)
            options_to_preview_mapping[session_name] = _session_preview(session)
        msg = "Choose a Herdr session to kill:"

    selections = interactive_choose_with_preview(
        msg=msg,
        options_to_preview_mapping=options_to_preview_mapping,
        multi=True,
    )
    if len(selections) == 0:
        return ("error", "No Herdr target selected.")
    scripts: list[str] = []
    seen: set[str] = set()
    for selection in selections:
        if selection in seen:
            continue
        seen.add(selection)
        script = options_to_script.get(selection)
        if script is None:
            return ("error", f"Unknown Herdr target selected: {selection}")
        scripts.append(script)
    return ("run_script", "\n".join(scripts))
