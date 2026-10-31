from functools import cache
import json
import platform
import re
from subprocess import TimeoutExpired
from typing import cast

from stackops.scripts.python.helpers.helpers_sessions._attach_common import natural_sort_key, run_command
from stackops.scripts.python.helpers.helpers_sessions._zellij_backend_models import PaneEntry, SessionEntry, TabEntry


@cache
def require_zellij() -> None:
    if platform.system() == "Windows":
        raise ValueError("The zellij multiplexer requires macOS or Linux.")
    try:
        result = run_command(["zellij", "--version"])
    except (OSError, TimeoutExpired) as error:
        raise ValueError(f"""Unable to run Zellij: {error}""") from error
    match = re.fullmatch(r"zellij (\d+)\.(\d+)\.(\d+)(?:\S*)", result.stdout.strip())
    if result.returncode != 0 or match is None:
        raise ValueError("Unable to determine the installed Zellij version.")
    if tuple(int(part) for part in match.groups()) < (0, 45, 0):
        raise ValueError(f"""The Zellij backend requires Zellij 0.45 or newer; found {result.stdout.strip()}. Upgrade `zellij` to use this backend.""")


def run_zellij(args: list[str]) -> str:
    require_zellij()
    try:
        result = run_command(["zellij", *args])
    except (OSError, TimeoutExpired) as error:
        raise ValueError(f"""Unable to run Zellij: {error}""") from error
    if result.returncode != 0:
        if args == ["list-sessions", "--no-formatting"] and result.stderr.strip() == "No active zellij sessions found.":
            return ""
        detail = result.stderr.strip() or result.stdout.strip()
        raise ValueError(f"""Zellij {' '.join(args)} failed: {detail}""")
    return result.stdout


def list_session_entries() -> list[SessionEntry]:
    sessions: list[SessionEntry] = []
    for line in run_zellij(["list-sessions", "--no-formatting"]).splitlines():
        name, separator, status = line.rpartition(" [Created ")
        if not separator or not name:
            raise ValueError(f"""Zellij returned an invalid session entry: {line}""")
        sessions.append(SessionEntry(name=name, exited=status.rstrip().endswith("(EXITED - attach to resurrect)")))
    sessions.sort(key=lambda session: (session.exited, natural_sort_key(session.name)))
    return sessions


def list_session_names() -> list[str]:
    sessions = list_session_entries()
    return [session.name for session in sessions if not session.exited]


def _json_entries(args: list[str]) -> list[dict[str, object]]:
    try:
        payload: object = json.loads(run_zellij(args))
    except json.JSONDecodeError as error:
        raise ValueError("Zellij returned invalid JSON.") from error
    if not isinstance(payload, list) or any(not isinstance(entry, dict) for entry in payload):
        raise ValueError("Zellij returned an invalid entry list.")
    return cast(list[dict[str, object]], payload)


def _field[T](entry: dict[str, object], key: str, kind: type[T]) -> T:
    value = entry.get(key)
    if not isinstance(value, kind):
        raise ValueError(f"""Zellij returned an invalid {key}.""")
    return value


def _optional_string(entry: dict[str, object], key: str) -> str:
    value = entry.get(key)
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError(f"""Zellij returned an invalid {key}.""")
    return value


def list_tab_entries(session_name: str) -> list[TabEntry]:
    entries = _json_entries(["--session", session_name, "action", "list-tabs", "--json"])
    tabs = [TabEntry(
        tab_id=_field(entry, "tab_id", int),
        position=_field(entry, "position", int),
        name=_field(entry, "name", str),
        active=_field(entry, "active", bool),
    ) for entry in entries]
    tabs.sort(key=lambda tab: tab.position)
    return tabs


def list_pane_entries(session_name: str) -> list[PaneEntry]:
    entries = _json_entries(["--session", session_name, "action", "list-panes", "--all", "--json"])
    panes: list[PaneEntry] = []
    for entry in entries:
        if _field(entry, "is_plugin", bool):
            continue
        exit_status = entry.get("exit_status")
        if exit_status is not None and not isinstance(exit_status, int):
            raise ValueError("Zellij returned an invalid pane exit status.")
        panes.append(PaneEntry(
            pane_id=f"""terminal_{_field(entry, 'id', int)}""",
            tab_id=_field(entry, "tab_id", int),
            tab_position=_field(entry, "tab_position", int),
            tab_name=_field(entry, "tab_name", str),
            title=_field(entry, "title", str),
            command=_optional_string(entry, "pane_command"),
            terminal_command=_optional_string(entry, "terminal_command"),
            cwd=_optional_string(entry, "pane_cwd"),
            exited=_field(entry, "exited", bool),
            exit_status=exit_status,
            is_held=_field(entry, "is_held", bool),
            focused=_field(entry, "is_focused", bool),
            x=_field(entry, "pane_x", int),
            y=_field(entry, "pane_y", int),
        ))
    panes.sort(key=lambda pane: (pane.tab_position, pane.y, pane.x, pane.pane_id))
    return panes
