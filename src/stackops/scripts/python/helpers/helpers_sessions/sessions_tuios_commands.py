import json
import shlex
from pathlib import Path
from typing import cast

from stackops.cluster.sessions_managers.session_exit_mode import SessionExitMode
from stackops.scripts.python.helpers.helpers_sessions._tuios_backend_state import kill_window_command, run_tuios
from stackops.utils.schemas.layouts.layout_types import TabConfig


def build_window_script(command: str, exit_mode: SessionExitMode) -> str:
    run_command = rf"""printf '\033]133;A\007$ \033]133;B\007%s\n\033]133;C\007' {shlex.quote(command)}
bash -c {shlex.quote(command)}
stackops_exit_code=$?
printf '\033]133;D;%s\007' "$stackops_exit_code"
"""
    match exit_mode:
        case "backToShell":
            return run_command + '''exec "${SHELL:-bash}" -i'''
        case "killWindow":
            return run_command + '''exit "$stackops_exit_code"'''
        case "terminate":
            return rf"""while true; do
{run_command}
printf '\nProcess completed with exit code %s. Press Enter to restart, or type anything and press Enter to close.\n' "$stackops_exit_code"
if ! IFS= read -r stackops_restart_reply || [ -n "$stackops_restart_reply" ]; then
    exit "$stackops_exit_code"
fi
done"""


def launch_window(session_name: str, tab: TabConfig, exit_mode: SessionExitMode) -> str:
    output = run_tuios(
        [
            "call", "new-window",
            json.dumps({
                "session": session_name,
                "cwd": str(Path(tab["startDir"]).expanduser().absolute()),
                "workspace": 1,
                "focus": False,
                "name": tab["tabName"],
                "close_on_exit": True,
                "command": ["bash", "-c", build_window_script(command=tab["command"], exit_mode=exit_mode)],
            }),
        ]
    )
    try:
        payload: object = json.loads(output)
    except json.JSONDecodeError as error:
        raise ValueError("TUIOS returned invalid new-window JSON.") from error
    if not isinstance(payload, dict):
        raise ValueError("TUIOS returned an invalid new-window response.")
    window_id = cast(dict[str, object], payload).get("window_id")
    if not isinstance(window_id, str) or not window_id:
        raise ValueError(f"""TUIOS did not return an ID for window '{tab['tabName']}'.""")
    return window_id


def close_window(session_name: str, window_id: str) -> None:
    run_tuios(
        kill_window_command(session_name=session_name, window_id=window_id)[1:]
    )
