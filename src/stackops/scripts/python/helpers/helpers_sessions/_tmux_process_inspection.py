from dataclasses import dataclass
from pathlib import Path

import psutil


SHELL_COMMAND_NAMES: frozenset[str] = frozenset(
    {
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
)
_ACTIVE_PROCESS_STATUSES: frozenset[str] = frozenset(
    {
        "running",
        "sleeping",
        "disk-sleep",
        "idle",
        "waking",
        "parked",
    }
)


@dataclass(frozen=True)
class PaneProcess:
    pid: int
    name: str
    argv: tuple[str, ...]
    depth: int
    started_at: float


def normalized_command_name(command_name: str) -> str:
    stripped_name = command_name.strip()
    while stripped_name.startswith("-"):
        stripped_name = stripped_name[1:]
    if stripped_name == "":
        return ""
    return Path(stripped_name).name.casefold()


def process_command_name_candidates(process: PaneProcess) -> set[str]:
    candidates: set[str] = set()
    name_candidate = normalized_command_name(process.name)
    if name_candidate != "":
        candidates.add(name_candidate)
    if len(process.argv) > 0:
        argv_candidate = normalized_command_name(process.argv[0])
        if argv_candidate != "":
            candidates.add(argv_candidate)
    return candidates


def is_shell_command_name(command_name: str) -> bool:
    return normalized_command_name(command_name) in SHELL_COMMAND_NAMES


def is_shell_process(process: PaneProcess) -> bool:
    return not process_command_name_candidates(process).isdisjoint(SHELL_COMMAND_NAMES)


def safe_process_name(process: psutil.Process) -> str:
    try:
        return process.name().strip()
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return ""


def safe_process_cmdline(process: psutil.Process) -> tuple[str, ...]:
    try:
        return tuple(part for part in process.cmdline() if part)
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return ()


def is_active_process(process: psutil.Process) -> bool:
    try:
        return process.is_running() and process.status() in _ACTIVE_PROCESS_STATUSES
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return False


def _safe_process_started_at(process: psutil.Process) -> float:
    try:
        return process.create_time()
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return 0.0


def _process_snapshot(process: psutil.Process, depth: int) -> PaneProcess | None:
    if not is_active_process(process):
        return None
    process_name = safe_process_name(process)
    process_argv = safe_process_cmdline(process)
    if process_name == "" and len(process_argv) == 0:
        return None
    return PaneProcess(
        pid=process.pid,
        name=process_name,
        argv=process_argv,
        depth=depth,
        started_at=_safe_process_started_at(process),
    )


def _collect_active_child_processes(process: psutil.Process, child_depth: int) -> list[PaneProcess]:
    try:
        child_processes = process.children()
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return []

    collected_processes: list[PaneProcess] = []
    for child_process in child_processes:
        child_snapshot = _process_snapshot(process=child_process, depth=child_depth)
        if child_snapshot is not None:
            collected_processes.append(child_snapshot)
        collected_processes.extend(
            _collect_active_child_processes(
                process=child_process,
                child_depth=child_depth + 1,
            )
        )
    return collected_processes


def collect_active_pane_processes(pane_pid: str) -> list[PaneProcess]:
    if not pane_pid.isdigit():
        return []
    try:
        root_process = psutil.Process(int(pane_pid))
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return []

    collected_processes: list[PaneProcess] = []
    root_snapshot = _process_snapshot(process=root_process, depth=0)
    if root_snapshot is not None:
        collected_processes.append(root_snapshot)
    collected_processes.extend(
        _collect_active_child_processes(
            process=root_process,
            child_depth=1,
        )
    )
    return collected_processes
