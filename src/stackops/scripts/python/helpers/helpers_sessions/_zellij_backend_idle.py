import os
from shlex import join, split

from stackops.scripts.python.helpers.helpers_sessions._tmux_process_inspection import is_shell_command_name
from stackops.scripts.python.helpers.helpers_sessions._zellij_backend_models import PaneEntry
from stackops.scripts.python.helpers.helpers_sessions._zellij_backend_state import list_pane_entries
from stackops.scripts.python.helpers.helpers_sessions.kill_models import KilledTarget


def pane_is_idle(pane: PaneEntry) -> bool | None:
    if pane.exited or pane.is_held:
        return False
    if not pane.command:
        return None
    try:
        arguments = split(pane.command)
    except ValueError:
        return None
    if not arguments or not is_shell_command_name(arguments[0]):
        return False
    return all(argument in {"-l", "-i", "-il", "-li", "--login", "--interactive"} for argument in arguments[1:])


def build_idle_kill_script_for_sessions(session_names: list[str]) -> tuple[str, list[KilledTarget]]:
    commands: list[str] = []
    killed_targets: list[KilledTarget] = []
    for session_name in session_names:
        panes = list_pane_entries(session_name)
        idle_panes = [pane for pane in panes if pane_is_idle(pane) is True]
        if session_name == os.environ.get("ZELLIJ_SESSION_NAME"):
            current_pane_id = f"""terminal_{os.environ.get('ZELLIJ_PANE_ID', '')}"""
            idle_panes.sort(key=lambda pane: pane.pane_id == current_pane_id)
        if panes and len(idle_panes) == len(panes):
            commands.append(join(["zellij", "kill-session", "--", session_name]))
            killed_targets.append(KilledTarget(
                action="session", session=session_name, window="-", detail=f"""{len(panes)} idle pane(s)""",
            ))
            continue
        for pane in idle_panes:
            commands.append(join(["zellij", "--session", session_name, "action", "close-pane", "--pane-id", pane.pane_id]))
            killed_targets.append(KilledTarget(
                action="pane", session=session_name, window=pane.tab_name, detail=pane.pane_id,
            ))
    return "\n".join(commands), killed_targets
