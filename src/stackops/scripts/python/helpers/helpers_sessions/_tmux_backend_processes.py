from typing import Callable

from stackops.scripts.python.helpers.helpers_sessions._tmux_process_inspection import (
    PaneProcess,
    collect_active_pane_processes,
    is_shell_command_name,
    is_shell_process,
)


def _process_sort_key(process: PaneProcess) -> tuple[int, float, int]:
    return (process.depth, process.started_at, process.pid)


def _format_process_label(process: PaneProcess) -> str:
    if len(process.argv) == 0:
        return process.name or "—"

    head = process.argv[0].split("/")[-1] or process.name or process.argv[0]
    detail = ""
    for arg in process.argv[1:]:
        if not arg or arg.startswith("-"):
            continue
        detail = arg.split("/")[-1] if "/" in arg else arg
        break
    return f"{head} {detail}".strip()


def find_meaningful_pane_process_label(pane_pid: str) -> str | None:
    descendants = [
        process
        for process in collect_active_pane_processes(pane_pid=pane_pid)
        if process.depth > 0
    ]

    non_shell_descendants = [
        process
        for process in descendants
        if not is_shell_process(process=process)
    ]
    if non_shell_descendants:
        chosen = max(non_shell_descendants, key=_process_sort_key)
        return _format_process_label(chosen)

    meaningful_shells = [
        process
        for process in descendants
        if is_shell_process(process=process)
        and len(process.argv) > 1
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
    cmd = pane["pane_command"]
    if is_shell_command_name(command_name=cmd):
        child_process = pane_process_label_finder(pane.get("pane_pid", ""))
        if child_process:
            return child_process, f"running: `{child_process}`"
        return process_name, "idle shell"
    if cmd:
        return process_name, f"running: `{pane['pane_command']}`"
    return process_name, "unknown"
