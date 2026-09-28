import psutil

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


def window_is_idle(session_name: str, window: WindowEntry) -> bool | None:
    if window.agent_state != "none" or window.running_command or window.at_prompt is False:
        return False
    if window.host:
        return None
    pane_processes: dict[int, int] = {}
    try:
        for process in psutil.process_iter():
            try:
                environment = process.environ()
                if environment.get("TUIOS_PANE_ID") == window.window_id and environment.get("TUIOS_SESSION") == session_name:
                    pane_processes[process.pid] = process.ppid()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    except (PermissionError, psutil.AccessDenied):
        return None
    root_pids = [pid for pid, parent_pid in pane_processes.items() if parent_pid not in pane_processes]
    if len(root_pids) != 1:
        return None
    processes = collect_active_pane_processes(pane_pid=str(root_pids[0]))
    if not processes or not is_shell_process(processes[0]):
        return False if processes else None
    if any(argument.startswith("-") and "c" in argument[1:] for argument in processes[0].argv[1:]):
        return False
    return all(is_shell_process(process) and len(process.argv) <= 1 for process in processes[1:])


def build_idle_kill_script_for_sessions(session_names: list[str]) -> tuple[str, list[KilledTarget]]:
    commands: list[str] = []
    killed_targets: list[KilledTarget] = []
    for session_name in session_names:
        windows = list_window_entries(session_name)
        idle_windows = [window for window in windows if window_is_idle(session_name, window) is True]
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
