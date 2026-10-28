from stackops.scripts.python.helpers.helpers_sessions._attach_common import quote
from stackops.scripts.python.helpers.helpers_sessions._tmux_process_inspection import (
    collect_active_pane_processes,
    is_shell_process,
)
from stackops.scripts.python.helpers.helpers_sessions._tuios_backend_models import WindowEntry
from stackops.scripts.python.helpers.helpers_sessions._tuios_backend_state import (
    kill_window_command,
    list_window_entries,
)
from stackops.scripts.python.helpers.helpers_sessions.kill_models import KilledTarget


def window_is_idle(window: WindowEntry) -> bool | None:
    if window.agent_state != "none" or window.running_command or window.at_prompt is False:
        return False
    if window.host or window.pid <= 0:
        return None
    try:
        processes = collect_active_pane_processes(pane_pid=str(window.pid))
    except PermissionError:
        return None
    if not processes or not is_shell_process(processes[0]):
        return False if processes else None
    if any(
        argument == "--command" or (argument.startswith("-") and not argument.startswith("--") and "c" in argument[1:])
        for argument in processes[0].argv[1:]
    ):
        return False
    return all(is_shell_process(process) and len(process.argv) <= 1 for process in processes[1:])


def build_idle_kill_script_for_sessions(session_names: list[str]) -> tuple[str, list[KilledTarget]]:
    commands: list[str] = []
    killed_targets: list[KilledTarget] = []
    for session_name in session_names:
        windows = list_window_entries(session_name)
        idle_windows = [window for window in windows if window_is_idle(window=window) is True]
        if windows and len(idle_windows) == len(windows):
            commands.append(f"""tuios kill-session -- {quote(session_name)}""")
            killed_targets.append(KilledTarget(
                action="session", session=session_name, window="-", detail=f"""{len(windows)} idle window(s)""",
            ))
            continue
        for window in idle_windows:
            commands.append(" ".join(quote(argument) for argument in kill_window_command(session_name, window.window_id)))
            killed_targets.append(KilledTarget(
                action="window", session=session_name, window=window.display_name, detail=window.window_id,
            ))
    return "\n".join(commands), killed_targets
