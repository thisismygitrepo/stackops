from collections import defaultdict
from pathlib import Path

import psutil

from machineconfig.scripts.python.helpers.helpers_sessions.attach_impl import (
    KILL_ALL_AND_NEW_LABEL,
    NEW_SESSION_LABEL,
    interactive_choose_with_preview,
    natural_sort_key,
    quote,
    run_command,
    strip_ansi_codes,
)


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


def _find_meaningful_pane_process_label(pane_pid: str) -> str | None:
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


def _classify_pane_status(pane: dict[str, str]) -> tuple[str, str]:
    process_name = pane["pane_command"] or "—"
    if pane["pane_dead"]:
        exit_code = pane.get("pane_dead_status", "?")
        return process_name, f"exited (code {exit_code})"
    cmd = pane["pane_command"].lower()
    if cmd in _SHELL_COMMANDS:
        child_process = _find_meaningful_pane_process_label(pane.get("pane_pid", ""))
        if child_process:
            return child_process, f"running: `{child_process}`"
        return process_name, "idle shell"
    if cmd:
        return process_name, f"running: `{pane['pane_command']}`"
    return process_name, "unknown"


def _build_preview(session_name: str) -> str:
    lines: list[str] = [f"# Session: {session_name}", "", "**backend:** tmux"]
    windows_result = run_command(
        [
            "tmux",
            "list-windows",
            "-t",
            session_name,
            "-F",
            "#{window_index}\t#{window_name}\t#{window_panes}\t#{?window_active,active,}",
        ]
    )
    if windows_result.returncode != 0:
        error_text = (windows_result.stderr or windows_result.stdout or "No preview data available").strip()
        lines += ["", error_text]
        return "\n".join(lines)

    panes_result = run_command(
        [
            "tmux",
            "list-panes",
            "-s",
            "-t",
            session_name,
            "-F",
            "#{window_index}\t#{pane_index}\t#{pane_current_path}\t#{pane_current_command}\t#{?pane_active,active,}\t#{?pane_dead,dead,}\t#{pane_dead_status}\t#{pane_pid}",
        ]
    )

    window_lines = [line for line in windows_result.stdout.splitlines() if line.strip()]
    lines.append(f"  |  **windows:** {len(window_lines)}")
    lines.append("")

    panes_by_window: dict[str, list[dict[str, str]]] = defaultdict(list)
    if panes_result.returncode == 0:
        for pane_line in panes_result.stdout.splitlines():
            if not pane_line.strip():
                continue
            parts = pane_line.split("\t")
            while len(parts) < 8:
                parts.append("")
            (
                win_idx,
                pane_idx,
                pane_cwd,
                pane_cmd,
                pane_active,
                pane_dead,
                pane_dead_status,
                pane_pid,
            ) = parts[:8]
            panes_by_window[win_idx].append(
                {
                    "pane_index": pane_idx.strip(),
                    "pane_cwd": pane_cwd.strip(),
                    "pane_command": pane_cmd.strip(),
                    "pane_active": pane_active.strip(),
                    "pane_dead": pane_dead.strip(),
                    "pane_dead_status": pane_dead_status.strip(),
                    "pane_pid": pane_pid.strip(),
                }
            )

    # --- Windows summary table ---
    lines.append("## Windows")
    lines.append("")
    lines.append("| # | Name | Panes | Active |")
    lines.append("|---|------|-------|--------|")
    for window_line in window_lines:
        parts = window_line.split("\t")
        while len(parts) < 4:
            parts.append("")
        w_idx, w_name, w_panes, w_active = parts[0].strip(), parts[1].strip(), parts[2].strip(), parts[3].strip()
        active_mark = "**yes**" if w_active else ""
        lines.append(f"| {w_idx} | {w_name} | {w_panes} | {active_mark} |")
    lines.append("")

    # --- Merged pane details table ---
    lines.append("## Pane Details")
    lines.append("")
    lines.append("| Window# | WindowName | Pane | Process | Status | Directory |")
    lines.append("|---------|------------|------|---------|--------|-----------|")
    for window_line in window_lines:
        parts = window_line.split("\t")
        while len(parts) < 4:
            parts.append("")
        w_idx, w_name = parts[0].strip(), parts[1].strip()
        window_panes_list = sorted(
            panes_by_window.get(w_idx, []),
            key=lambda p: int(p["pane_index"]) if p["pane_index"].isdigit() else p["pane_index"],
        )
        if not window_panes_list:
            lines.append(f"| {w_idx} | {w_name} | — | — | — | — |")
            continue
        for pane in window_panes_list:
            process_name, status = _classify_pane_status(pane)
            cwd = pane["pane_cwd"] or "—"
            active_flag = " ⇐" if pane["pane_active"] else ""
            lines.append(
                f"| {w_idx} | {w_name} | {pane['pane_index']}{active_flag} | {process_name} | {status} | `{cwd}` |"
            )
    lines.append("")

    if panes_result.returncode != 0:
        lines.append(f"> ⚠ pane query warning: {(panes_result.stderr or panes_result.stdout).strip()}")
    return "\n".join(lines)


def choose_session(name: str | None, new_session: bool, kill_all: bool) -> tuple[str, str | None]:
    if name is not None:
        return ("run_script", f"tmux attach -t {quote(name)}")
    if new_session:
        cmd = "tmux new-session"
        if kill_all:
            cmd = f"tmux kill-server\n{cmd}"
        return ("run_script", cmd)
    result = run_command(["tmux", "list-sessions", "-F", "#S"])
    sessions = result.stdout.strip().splitlines() if result.returncode == 0 else []
    sessions = [s for s in sessions if s.strip()]
    sessions.sort(key=lambda s: natural_sort_key(strip_ansi_codes(s).split(" [Created")[0].strip()))
    if len(sessions) == 0:
        return ("run_script", "tmux new-session")
    if len(sessions) == 1:
        return ("run_script", f"tmux attach -t {quote(sessions[0])}")

    options_to_preview_mapping = {session_name: _build_preview(session_name) for session_name in sessions}
    options_to_preview_mapping[NEW_SESSION_LABEL] = "backend: tmux\naction: create a fresh session\n\ntmux new-session"
    options_to_preview_mapping[KILL_ALL_AND_NEW_LABEL] = "backend: tmux\naction: kill the tmux server, then start a new session\n\ntmux kill-server\ntmux new-session"
    session_name = interactive_choose_with_preview(msg="Choose a tmux session to attach to:", options_to_preview_mapping=options_to_preview_mapping)
    if session_name is None:
        return ("error", "No tmux session selected.")
    if session_name == NEW_SESSION_LABEL:
        cmd = "tmux new-session"
        if kill_all:
            cmd = f"tmux kill-server\n{cmd}"
        return ("run_script", cmd)
    if session_name == KILL_ALL_AND_NEW_LABEL:
        return ("run_script", "tmux kill-server\ntmux new-session")
    return ("run_script", f"tmux attach -t {quote(session_name)}")
