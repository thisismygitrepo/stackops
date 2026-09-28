import json
from subprocess import TimeoutExpired
from typing import cast

from stackops.scripts.python.helpers.helpers_sessions._attach_common import (
    natural_sort_key,
    run_command,
)
from stackops.scripts.python.helpers.helpers_sessions._tuios_backend_models import (
    SessionEntry,
    WindowEntry,
)


type JsonObject = dict[str, object]


def run_tuios(args: list[str]) -> str:
    try:
        result = run_command(["tuios", *args])
    except (OSError, TimeoutExpired) as error:
        raise ValueError(f"""Unable to run TUIOS: {error}""") from error
    if result.returncode != 0 and not (args == ["ls", "--json"] and result.returncode == 3):
        detail = result.stderr.strip() or result.stdout.strip()
        raise ValueError(f"""TUIOS {' '.join(args)} failed: {detail}""")
    return result.stdout


def _json_entries(value: object) -> list[JsonObject]:
    if not isinstance(value, list) or any(not isinstance(entry, dict) for entry in value):
        raise ValueError("TUIOS returned an invalid entry list.")
    return cast(list[JsonObject], value)


def _field[T](entry: JsonObject, key: str, kind: type[T], missing: T) -> T:
    value = entry.get(key, missing)
    if not isinstance(value, kind):
        raise ValueError(f"""TUIOS returned an invalid {key}.""")
    return value


def list_session_entries() -> list[SessionEntry]:
    try:
        payload: object = json.loads(run_tuios(["ls", "--json"]))
    except json.JSONDecodeError as error:
        raise ValueError("TUIOS returned invalid session JSON.") from error
    sessions: list[SessionEntry] = []
    for entry in _json_entries(payload):
        name = _field(entry, "name", str, "")
        if not name:
            raise ValueError("TUIOS returned a session without a name.")
        sessions.append(SessionEntry(
            name=name,
            id=_field(entry, "id", str, ""),
            window_count=_field(entry, "window_count", int, 0),
            attached=_field(entry, "attached", bool, False),
            saved=_field(entry, "saved", bool, False),
            last_active=_field(entry, "last_active", int, 0),
        ))
    sessions.sort(key=lambda session: (session.saved, natural_sort_key(session.name)))
    return sessions


def list_window_entries(session_name: str) -> list[WindowEntry]:
    try:
        payload: object = json.loads(run_tuios(["list-windows", "--session", session_name, "--json"]))
    except json.JSONDecodeError as error:
        raise ValueError("TUIOS returned invalid window JSON.") from error
    if not isinstance(payload, dict):
        raise ValueError("TUIOS returned an invalid window response.")
    windows: list[WindowEntry] = []
    for entry in _json_entries(payload.get("windows")):
        window_id = _field(entry, "window_id", str, "")
        if not window_id:
            raise ValueError("TUIOS returned a window without an ID.")
        at_prompt = entry.get("at_prompt")
        last_exit_code = entry.get("last_exit_code")
        if at_prompt is not None and not isinstance(at_prompt, bool):
            raise ValueError("TUIOS returned an invalid at_prompt state.")
        if last_exit_code is not None and not isinstance(last_exit_code, int):
            raise ValueError("TUIOS returned an invalid last_exit_code.")
        windows.append(WindowEntry(
            window_id=window_id,
            index=_field(entry, "index", int, 0),
            workspace=_field(entry, "workspace", int, 1),
            display_name=_field(entry, "display_name", str, ""),
            focused=_field(entry, "focused", bool, False),
            cwd=_field(entry, "cwd", str, ""),
            agent_state=_field(entry, "agent_state", str, "none"),
            host=_field(entry, "host", str, ""),
            at_prompt=at_prompt,
            last_exit_code=last_exit_code,
            foreground_command=_field(entry, "foreground_cmd", str, ""),
            command_seq=_field(entry, "command_seq", int, 0),
            running_command=_field(entry, "running_cmdline", str, ""),
            last_command=_field(entry, "last_cmdline", str, ""),
        ))
    windows.sort(key=lambda window: (window.workspace, window.index))
    return windows


def capture_window(session_name: str, window_id: str, lines: int, ansi: bool) -> str:
    args = ["capture-pane", "--session", session_name, "--window", window_id, "--scrollback", "--lines", str(lines)]
    if ansi:
        args.append("--ansi")
    return run_tuios(args)


def kill_window_command(session_name: str, window_id: str) -> list[str]:
    command = ["tuios", "run-command", "--session", session_name]
    command.extend(("CloseWindow", window_id))
    return command
