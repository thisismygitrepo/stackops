from pathlib import Path
from typing import Callable

import psutil


_SHELL_COMMANDS: set[str] = {
    "bash",
    "zsh",
    "fish",
    "sh",
    "dash",
    "ksh",
    "tcsh",
    "csh",
    "nu",
    "nushell",
    "pwsh",
    "powershell",
    "elvish",
    "xonsh",
    "oil",
}
_ACTIVE_PROCESS_STATUSES: set[str] = {
    "running",
    "sleeping",
    "disk-sleep",
    "idle",
    "waking",
    "parked",
}


def _safe_process_name(proc: psutil.Process) -> str:
    try:
        return proc.name().strip()
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return ""


def _safe_process_cmdline(proc: psutil.Process) -> list[str]:
    try:
        return [part for part in proc.cmdline() if part]
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return []


def _is_active_process(proc: psutil.Process) -> bool:
    try:
        return proc.is_running() and proc.status() in _ACTIVE_PROCESS_STATUSES
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return False


def _process_sort_key(proc: psutil.Process) -> tuple[int, float, int]:
    depth = 0
    current = proc
    while True:
        try:
            parent = current.parent()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            break
        if parent is None:
            break
        depth += 1
        current = parent
    try:
        create_time = proc.create_time()
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        create_time = 0.0
    return (depth, create_time, proc.pid)


def _format_process_label(proc: psutil.Process) -> str:
    proc_name = _safe_process_name(proc)
    cmdline = _safe_process_cmdline(proc)
    if not cmdline:
        return proc_name or "—"

    head = Path(cmdline[0]).name or proc_name or cmdline[0]
    detail = ""
    for arg in cmdline[1:]:
        if not arg or arg.startswith("-"):
            continue
        detail = Path(arg).name if "/" in arg else arg
        break
    return f"{head} {detail}".strip()


def find_meaningful_pane_process_label(pane_pid: str) -> str | None:
    if not pane_pid.isdigit():
        return None
    try:
        root_proc = psutil.Process(int(pane_pid))
        descendants = [proc for proc in root_proc.children(recursive=True) if _is_active_process(proc)]
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return None

    non_shell_descendants = [
        proc for proc in descendants if _safe_process_name(proc).lower() not in _SHELL_COMMANDS
    ]
    if non_shell_descendants:
        chosen = max(non_shell_descendants, key=_process_sort_key)
        return _format_process_label(chosen)

    meaningful_shells = [
        proc
        for proc in descendants
        if _safe_process_name(proc).lower() in _SHELL_COMMANDS
        and len(_safe_process_cmdline(proc)) > 1
    ]
    if meaningful_shells:
        chosen = max(meaningful_shells, key=_process_sort_key)
        return _format_process_label(chosen)

    return None


def classify_pane_status(
    pane: dict[str, str],
    pane_process_label_finder: Callable[[str], str | None],
) -> tuple[str, str]:
    process_name = pane["pane_command"] or "—"
    if pane["pane_dead"]:
        exit_code = pane.get("pane_dead_status", "?")
        return process_name, f"exited (code {exit_code})"
    cmd = pane["pane_command"].lower()
    if cmd in _SHELL_COMMANDS:
        child_process = pane_process_label_finder(pane.get("pane_pid", ""))
        if child_process:
            return child_process, f"running: `{child_process}`"
        return process_name, "idle shell"
    if cmd:
        return process_name, f"running: `{pane['pane_command']}`"
    return process_name, "unknown"
