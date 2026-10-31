import os
from shlex import join as shell_command
import sys
from typing import Literal

from stackops.scripts.python.helpers.helpers_sessions._attach_common import (
    AttachSessionChoice,
    KILL_ALL_AND_NEW_LABEL,
    NEW_SESSION_LABEL,
    interactive_choose_with_preview,
)
from stackops.scripts.python.helpers.helpers_sessions._zellij_backend_models import PaneEntry, SessionEntry, TabEntry
from stackops.scripts.python.helpers.helpers_sessions._zellij_backend_preview import pane_label, pane_preview, session_preview, tab_label
from stackops.scripts.python.helpers.helpers_sessions._zellij_backend_state import list_pane_entries, list_session_entries, list_tab_entries


type TraceSessionChoice = tuple[Literal["error"], str] | tuple[Literal["session_names"], list[str]]


def get_session_preview(name: str) -> str:
    session = next((entry for entry in list_session_entries() if entry.name == name), None)
    if session is None:
        raise ValueError(f"""No Zellij session named '{name}' is available.""")
    return session_preview(session)


def choose_existing_session_names(msg: str) -> TraceSessionChoice:
    try:
        sessions = [session for session in list_session_entries() if not session.exited]
        previews = {session.name: session_preview(session) for session in sessions}
    except ValueError as error:
        return "error", str(error)
    if not previews:
        return "error", "No running Zellij sessions are available."
    selections = interactive_choose_with_preview(msg=msg, options_to_preview_mapping=previews, multi=True)
    if not selections:
        return "error", "No Zellij session selected."
    if any(name not in previews for name in selections):
        return "error", "An unknown Zellij session was selected."
    return "session_names", list(dict.fromkeys(selections))


def attach_session_script(name: str, tab: TabEntry | None, pane: PaneEntry | None) -> str:
    current_session = os.environ.get("ZELLIJ_SESSION_NAME")
    focus_args: list[str] = []
    switch_args = ["zellij", "action", "switch-session"]
    if pane is not None:
        focus_args = ["focus-pane-id", pane.pane_id]
        switch_args.extend(["--pane-id", pane.pane_id])
    elif tab is not None:
        focus_args = ["go-to-tab-by-id", str(tab.tab_id)]
        switch_args.extend(["--tab-position", str(tab.position + 1)])
    if current_session and current_session != name:
        return shell_command([*switch_args, "--", name])
    if not current_session and focus_args:
        arguments = [sys.executable, "-m", "stackops.scripts.python.helpers.helpers_sessions.zellij_attach"]
        if pane is not None:
            arguments.extend(["--pane-id", pane.pane_id])
        elif tab is not None:
            arguments.extend(["--tab-id", str(tab.tab_id)])
        return shell_command([*arguments, "--", name])
    commands: list[str] = []
    if focus_args and (pane is None or pane.pane_id != f"""terminal_{os.environ.get('ZELLIJ_PANE_ID', '')}"""):
        commands.append(shell_command(["zellij", "--session", name, "action", *focus_args]))
    if not current_session:
        commands.append(shell_command(["zellij", "attach", name]))
    return " &&\n".join(commands) if commands else ":"


def new_session_script(kill_all: bool, sessions: list[SessionEntry]) -> str:
    existing_names = {session.name for session in sessions}
    session_number = 0
    while f"""session-{session_number}""" in existing_names:
        session_number += 1
    name = f"""session-{session_number}"""
    current_session = os.environ.get("ZELLIJ_SESSION_NAME")
    running = sorted((session for session in sessions if not session.exited), key=lambda session: session.name == current_session)
    kill_commands = [shell_command(["zellij", "kill-session", "--", session.name]) for session in running if kill_all]
    if current_session:
        commands = [
            shell_command(["zellij", "action", "switch-session", "--", name]),
            *kill_commands,
        ]
    else:
        commands = [*kill_commands, shell_command(["zellij", "attach", "--create", name])]
    return " &&\n".join(commands)


def choose_session(name: str | None, new_session: bool, kill_all: bool, first: bool, window: bool) -> AttachSessionChoice:
    try:
        sessions = list_session_entries()
        if name is not None:
            if not any(session.name == name for session in sessions):
                return "error", f"""No Zellij session named '{name}' is available."""
            return "handoff_script", attach_session_script(name=name, tab=None, pane=None)
        if new_session or kill_all or not sessions:
            return "handoff_script", new_session_script(kill_all=kill_all, sessions=sessions)
        if first:
            return "handoff_script", attach_session_script(name=sessions[0].name, tab=None, pane=None)
        scripts: dict[str, str] = {}
        previews: dict[str, str] = {}
        for session in sessions:
            if not window:
                scripts[session.name] = attach_session_script(name=session.name, tab=None, pane=None)
                previews[session.name] = session_preview(session)
            elif not session.exited:
                panes = list_pane_entries(session.name)
                for tab in list_tab_entries(session.name):
                    label = tab_label(session.name, tab)
                    scripts[label] = attach_session_script(name=session.name, tab=tab, pane=None)
                    previews[label] = "\n\n".join(pane_preview(session.name, pane) for pane in panes if pane.tab_id == tab.tab_id)
                for pane in panes:
                    label = pane_label(session.name, pane)
                    scripts[label] = attach_session_script(name=session.name, tab=None, pane=pane)
                    previews[label] = pane_preview(session.name, pane)
        previews[NEW_SESSION_LABEL] = "backend: zellij\naction: create a new session"
        previews[KILL_ALL_AND_NEW_LABEL] = "backend: zellij\naction: kill every running session and create a new one"
        selection = interactive_choose_with_preview(
            msg="Choose a Zellij tab or pane:" if window else "Choose a Zellij session:",
            options_to_preview_mapping=previews,
            multi=False,
        )
    except ValueError as error:
        return "error", str(error)
    if selection is None:
        return "error", "No Zellij target selected."
    if selection in {NEW_SESSION_LABEL, KILL_ALL_AND_NEW_LABEL}:
        return "handoff_script", new_session_script(kill_all=selection == KILL_ALL_AND_NEW_LABEL, sessions=sessions)
    script = scripts.get(selection)
    if script is None:
        return "error", f"""Unknown Zellij target selected: {selection}"""
    return "handoff_script", script
