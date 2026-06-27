import shlex

from stackops.scripts.python.helpers.helpers_sessions._tmux_process_inspection import (
    PaneProcess,
    collect_active_pane_processes,
    is_shell_command_name,
    is_shell_process,
    normalized_command_name,
    process_command_name_candidates,
)


def _has_argv(process: PaneProcess) -> bool:
    return len(process.argv) > 0 and process.argv[0].strip() != ""


def _choose_closest_newest_process(processes: list[PaneProcess]) -> PaneProcess:
    return min(processes, key=lambda process: (process.depth, -process.started_at, -process.pid))


def _matching_processes(
    processes: list[PaneProcess],
    target_command_name: str,
) -> list[PaneProcess]:
    return [
        process
        for process in processes
        if target_command_name in process_command_name_candidates(process)
    ]


def select_current_pane_process_argv(
    pane_command: str,
    processes: list[PaneProcess],
) -> tuple[str, ...] | None:
    processes_with_argv = [process for process in processes if _has_argv(process=process)]
    if len(processes_with_argv) == 0:
        return None

    target_command_name = normalized_command_name(command_name=pane_command)
    if target_command_name != "" and not is_shell_command_name(command_name=pane_command):
        matching_processes = _matching_processes(
            processes=processes_with_argv,
            target_command_name=target_command_name,
        )
        if len(matching_processes) > 0:
            return _choose_closest_newest_process(processes=matching_processes).argv

        non_shell_processes = [
            process
            for process in processes_with_argv
            if not is_shell_process(process=process)
        ]
        if len(non_shell_processes) > 0:
            return _choose_closest_newest_process(processes=non_shell_processes).argv

    non_shell_descendants = [
        process
        for process in processes_with_argv
        if process.depth > 0 and not is_shell_process(process=process)
    ]
    if len(non_shell_descendants) > 0:
        return _choose_closest_newest_process(processes=non_shell_descendants).argv

    shell_processes_with_arguments = [
        process
        for process in processes_with_argv
        if is_shell_process(process=process) and len(process.argv) > 1
    ]
    if len(shell_processes_with_arguments) > 0:
        return _choose_closest_newest_process(processes=shell_processes_with_arguments).argv

    return None


def find_current_pane_command_line(pane: dict[str, str]) -> str | None:
    process_argv = select_current_pane_process_argv(
        pane_command=pane.get("pane_command", ""),
        processes=collect_active_pane_processes(pane_pid=pane.get("pane_pid", "")),
    )
    if process_argv is None:
        return None
    return shlex.join(list(process_argv))
