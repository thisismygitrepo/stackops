import os
from typing import Literal

from stackops.scripts.python.helpers.helpers_sessions._attach_common import (
    AttachSessionChoice,
    KILL_ALL_AND_NEW_LABEL,
    NEW_SESSION_LABEL,
    interactive_choose_with_preview,
    quote,
)
from stackops.scripts.python.helpers.helpers_sessions._tuios_backend_models import SessionEntry
from stackops.scripts.python.helpers.helpers_sessions._tuios_backend_preview import (
    session_preview,
    window_label,
    window_preview,
)
from stackops.scripts.python.helpers.helpers_sessions._tuios_backend_state import (
    list_session_entries,
    list_window_entries,
)


type TraceSessionChoice = tuple[Literal["error"], str] | tuple[Literal["session_names"], list[str]]


def list_session_names() -> list[str] | None:
    try:
        return [session.name for session in list_session_entries() if not session.saved]
    except ValueError:
        return None


def get_session_preview(name: str) -> str:
    sessions = list_session_entries()
    session = next((entry for entry in sessions if entry.name == name), None)
    if session is None:
        raise ValueError(f"""No TUIOS session named '{name}' is available.""")
    return session_preview(session)


def choose_existing_session_names(msg: str) -> TraceSessionChoice:
    try:
        sessions = [session for session in list_session_entries() if not session.saved]
        previews = {session.name: session_preview(session) for session in sessions}
    except ValueError as error:
        return "error", str(error)
    if not previews:
        return "error", "No running TUIOS sessions are available."
    selections = interactive_choose_with_preview(msg=msg, options_to_preview_mapping=previews, multi=True)
    if not selections:
        return "error", "No TUIOS session selected."
    for name in selections:
        if name not in previews:
            return "error", f"""Unknown TUIOS session selected: {name}"""
    return "session_names", list(dict.fromkeys(selections))


def new_session_script(kill_all: bool, sessions: list[SessionEntry]) -> str:
    running_sessions = [session for session in sessions if not session.saved]
    pane_id = os.environ.get("TUIOS_PANE_ID")
    if pane_id and kill_all:
        current_session = next((
            session.name for session in running_sessions
            if any(window.window_id == pane_id for window in list_window_entries(session.name))
        ), None)
        if current_session is None:
            raise ValueError("Cannot locate the current TUIOS pane's session to replace all sessions.")
        running_sessions.sort(key=lambda session: session.name == current_session)
    kill_commands = [f"""tuios kill-session -- {quote(session.name)}""" for session in running_sessions if kill_all]
    outside_script = " &&\n".join([*kill_commands, "tuios new"])
    existing_names = {session.name for session in sessions}
    session_number = 0
    while f"""session-{session_number}""" in existing_names:
        session_number += 1
    name = quote(f"""session-{session_number}""")
    inside_script = " &&\n".join([
        f"""tuios new --detach --cwd "$PWD" -- {name}""",
        f"""tuios switch-session -- {name}""",
        *kill_commands,
    ])
    return f"""if [ -n "${{TUIOS_PANE_ID:-}}" ]; then
{inside_script}
else
{outside_script}
fi"""


def attach_session_script(name: str) -> str:
    quoted_name = quote(name)
    return f"""if [ -n "${{TUIOS_PANE_ID:-}}" ]; then
    tuios switch-session -- {quoted_name}
else
    tuios attach -- {quoted_name}
fi"""


def choose_session(
    name: str | None,
    new_session: bool,
    kill_all: bool,
    first: bool,
    window: bool,
) -> AttachSessionChoice:
    if name is not None:
        return "handoff_script", attach_session_script(name)
    try:
        sessions = list_session_entries()
        if new_session or not sessions:
            return "handoff_script", new_session_script(kill_all=kill_all, sessions=sessions)
        if first:
            return "handoff_script", attach_session_script(sessions[0].name)
        scripts: dict[str, str] = {}
        previews: dict[str, str] = {}
        for session in sessions:
            if window:
                if session.saved:
                    continue
                for entry in list_window_entries(session.name):
                    label = window_label(session.name, entry)
                    scripts[label] = (
                        f"""tuios focus-window --session {quote(session.name)} -- {quote(entry.window_id)} &&\n"""
                        + attach_session_script(session.name)
                    )
                    previews[label] = window_preview(session.name, entry)
            else:
                scripts[session.name] = attach_session_script(session.name)
                previews[session.name] = session_preview(session)
        if window and len(scripts) == 1:
            return "handoff_script", next(iter(scripts.values()))
        previews[NEW_SESSION_LABEL] = "backend: tuios\naction: create a new session"
        if not kill_all:
            previews[KILL_ALL_AND_NEW_LABEL] = "backend: tuios\naction: kill every running session and create a new one"
        selection = interactive_choose_with_preview(
            msg="Choose a TUIOS window:" if window else "Choose a TUIOS session:",
            options_to_preview_mapping=previews,
        )
    except ValueError as error:
        return "error", str(error)
    if selection is None:
        return "error", "No TUIOS target selected."
    if selection in {NEW_SESSION_LABEL, KILL_ALL_AND_NEW_LABEL}:
        try:
            return "handoff_script", new_session_script(
                kill_all=kill_all or selection == KILL_ALL_AND_NEW_LABEL,
                sessions=sessions,
            )
        except ValueError as error:
            return "error", str(error)
    script = scripts.get(selection)
    if script is None:
        return "error", f"""Unknown TUIOS target selected: {selection}"""
    return "handoff_script", script
