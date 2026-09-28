import shlex
from pathlib import Path

from stackops.cluster.sessions_managers.session_exit_mode import SessionExitMode
from stackops.scripts.python.helpers.helpers_sessions._tuios_backend_state import run_tuios
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
    window_id = run_tuios(
        [
            "new-window",
            "--session", session_name,
            "--cwd", str(Path(tab["startDir"]).expanduser().absolute()),
            "--workspace", "1",
            "--no-focus",
            "--print-id",
            "--", tab["tabName"], "bash", "-c",
            build_window_script(command=tab["command"], exit_mode=exit_mode),
        ]
    ).strip()
    if not window_id:
        raise ValueError(f"""TUIOS did not return an ID for window '{tab['tabName']}'.""")
    return window_id


def close_window(session_name: str, window_id: str) -> None:
    run_tuios(
        ["run-command", "--session", session_name, "--", "CloseWindow", window_id]
    )
