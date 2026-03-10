from collections import defaultdict

from machineconfig.scripts.python.helpers.helpers_sessions.attach_impl import (
    KILL_ALL_AND_NEW_LABEL,
    NEW_SESSION_LABEL,
    interactive_choose_with_preview,
    natural_sort_key,
    quote,
    run_command,
    strip_ansi_codes,
)


def _build_preview(session_name: str) -> str:
    lines = ["backend: tmux", f"session: {session_name}"]
    windows_result = run_command(["tmux", "list-windows", "-t", session_name, "-F", "#{window_index}\t#{window_name}\t#{window_panes}\t#{?window_active,active,}"])
    if windows_result.returncode != 0:
        error_text = (windows_result.stderr or windows_result.stdout or "No preview data available").strip()
        lines.append("")
        lines.append(error_text)
        return "\n".join(lines)

    panes_result = run_command(["tmux", "list-panes", "-t", session_name, "-F", "#{window_index}\t#{pane_index}\t#{pane_title}\t#{pane_current_path}\t#{pane_current_command}\t#{?pane_active,active,}\t#{?pane_dead,dead,}"])

    window_lines = [line for line in windows_result.stdout.splitlines() if line.strip()]
    panes_by_window: dict[str, list[dict[str, str]]] = defaultdict(list)
    if panes_result.returncode == 0:
        for pane_line in panes_result.stdout.splitlines():
            if not pane_line.strip():
                continue
            parts = pane_line.split("\t")
            while len(parts) < 7:
                parts.append("")
            window_index, pane_index, pane_title, pane_cwd, pane_command, pane_active, pane_dead = parts[:7]
            panes_by_window[window_index].append({"pane_index": pane_index, "pane_title": pane_title.strip(), "pane_cwd": pane_cwd.strip(), "pane_command": pane_command.strip(), "pane_active": pane_active.strip(), "pane_dead": pane_dead.strip()})

    lines.append(f"windows: {len(window_lines)}")
    lines.append("")
    for window_line in window_lines:
        parts = window_line.split("\t")
        while len(parts) < 4:
            parts.append("")
        window_index, window_name, window_panes, window_active = parts[:4]
        active_suffix = " (active)" if window_active.strip() else ""
        lines.append(f"[{window_index}] {window_name} ({window_panes} pane{'s' if window_panes != '1' else ''}){active_suffix}")
        window_panes_list = sorted(panes_by_window.get(window_index, []), key=lambda pane: int(pane["pane_index"]) if pane["pane_index"].isdigit() else pane["pane_index"])
        if not window_panes_list:
            lines.append("  - (pane details unavailable)")
            continue
        for pane in window_panes_list:
            pane_name = pane["pane_title"] or pane["pane_command"] or f"pane {pane['pane_index']}"
            detail = pane["pane_command"] or "shell"
            if pane["pane_cwd"]:
                detail = f"{detail} [{pane['pane_cwd']}]"
            status_bits = [bit for bit in (pane["pane_active"], pane["pane_dead"]) if bit]
            status_suffix = f" ({', '.join(status_bits)})" if status_bits else ""
            if detail == pane_name:
                lines.append(f"  - {pane_name}{status_suffix}")
            else:
                lines.append(f"  - {pane_name}: {detail}{status_suffix}")

    if panes_result.returncode != 0:
        lines.append("")
        lines.append(f"pane query warning: {(panes_result.stderr or panes_result.stdout).strip()}")
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
