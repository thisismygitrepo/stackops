from collections import defaultdict
from subprocess import CompletedProcess
from typing import Callable


def session_sort_key(
    session_name: str,
    natural_sort_key_fn: Callable[[str], list[int | str]],
    strip_ansi_codes_fn: Callable[[str], str],
) -> list[int | str]:
    return natural_sort_key_fn(strip_ansi_codes_fn(session_name).split(" [Created")[0].strip())


def _window_sort_key(window: dict[str, str]) -> int | str:
    window_index = window["window_index"]
    return int(window_index) if window_index.isdigit() else window_index


def _pane_sort_key(pane: dict[str, str]) -> int | str:
    pane_index = pane["pane_index"]
    return int(pane_index) if pane_index.isdigit() else pane_index


def collect_session_snapshot(
    session_name: str,
    run_command_fn: Callable[[list[str]], CompletedProcess[str]],
) -> tuple[list[dict[str, str]] | None, dict[str, list[dict[str, str]]], str | None]:
    windows_result = run_command_fn(
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
        return (None, {}, error_text)

    windows: list[dict[str, str]] = []
    for window_line in windows_result.stdout.splitlines():
        if not window_line.strip():
            continue
        parts = window_line.split("\t")
        while len(parts) < 4:
            parts.append("")
        windows.append(
            {
                "window_index": parts[0].strip(),
                "window_name": parts[1].strip(),
                "window_panes": parts[2].strip(),
                "window_active": parts[3].strip(),
            }
        )
    windows.sort(key=_window_sort_key)

    panes_result = run_command_fn(
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

    panes_by_window: dict[str, list[dict[str, str]]] = defaultdict(list)
    pane_warning: str | None = None
    if panes_result.returncode == 0:
        for pane_line in panes_result.stdout.splitlines():
            if not pane_line.strip():
                continue
            parts = pane_line.split("\t")
            while len(parts) < 8:
                parts.append("")
            panes_by_window[parts[0].strip()].append(
                {
                    "pane_index": parts[1].strip(),
                    "pane_cwd": parts[2].strip(),
                    "pane_command": parts[3].strip(),
                    "pane_active": parts[4].strip(),
                    "pane_dead": parts[5].strip(),
                    "pane_dead_status": parts[6].strip(),
                    "pane_pid": parts[7].strip(),
                }
            )
        for pane_list in panes_by_window.values():
            pane_list.sort(key=_pane_sort_key)
    else:
        pane_warning = (panes_result.stderr or panes_result.stdout or "No pane data available").strip()

    return (windows, panes_by_window, pane_warning)


def _render_window_summary_table(windows: list[dict[str, str]]) -> list[str]:
    lines = ["## Windows", "", "| # | Name | Panes | Active |", "|---|------|-------|--------|"]
    for window in windows:
        active_mark = "**yes**" if window["window_active"] else ""
        lines.append(
            f"| {window['window_index']} | {window['window_name']} | {window['window_panes']} | {active_mark} |"
        )
    lines.append("")
    return lines


def _render_pane_details_table(
    windows: list[dict[str, str]],
    panes_by_window: dict[str, list[dict[str, str]]],
    classify_pane_status_fn: Callable[[dict[str, str]], tuple[str, str]],
) -> list[str]:
    lines = [
        "## Pane Details",
        "",
        "| Window# | WindowName | Pane | Process | Status | Directory |",
        "|---------|------------|------|---------|--------|-----------|",
    ]
    for window in windows:
        window_panes = panes_by_window.get(window["window_index"], [])
        if not window_panes:
            lines.append(f"| {window['window_index']} | {window['window_name']} | — | — | — | — |")
            continue
        for pane in window_panes:
            process_name, status = classify_pane_status_fn(pane)
            cwd = pane["pane_cwd"] or "—"
            active_flag = " ⇐" if pane["pane_active"] else ""
            lines.append(
                f"| {window['window_index']} | {window['window_name']} | {pane['pane_index']}{active_flag} | {process_name} | {status} | `{cwd}` |"
            )
    lines.append("")
    return lines


def build_preview(
    session_name: str,
    run_command_fn: Callable[[list[str]], CompletedProcess[str]],
    classify_pane_status_fn: Callable[[dict[str, str]], tuple[str, str]],
) -> str:
    lines: list[str] = [f"# Session: {session_name}", "", "**backend:** tmux"]
    windows, panes_by_window, pane_warning = collect_session_snapshot(session_name=session_name, run_command_fn=run_command_fn)
    if windows is None:
        return "\n".join(lines + ["", pane_warning or "No preview data available"])

    lines.append(f"  |  **windows:** {len(windows)}")
    lines.append("")
    lines.extend(_render_window_summary_table(windows))
    lines.extend(_render_pane_details_table(windows, panes_by_window, classify_pane_status_fn))
    if pane_warning:
        lines.append(f"> ⚠ pane query warning: {pane_warning}")
    return "\n".join(lines)


def build_window_preview(
    session_name: str,
    window: dict[str, str],
    panes: list[dict[str, str]],
    pane_warning: str | None,
    classify_pane_status_fn: Callable[[dict[str, str]], tuple[str, str]],
) -> str:
    lines = [
        f"# Session: {session_name}",
        "",
        "**backend:** tmux",
        f"**window:** {window['window_index']}:{window['window_name']}",
        "",
        "| Pane | Process | Status | Directory |",
        "|------|---------|--------|-----------|",
    ]
    if not panes:
        lines.append("| — | — | — | — |")
    for pane in panes:
        process_name, status = classify_pane_status_fn(pane)
        cwd = pane["pane_cwd"] or "—"
        active_flag = " ⇐" if pane["pane_active"] else ""
        lines.append(f"| {pane['pane_index']}{active_flag} | {process_name} | {status} | `{cwd}` |")
    lines.append("")
    if pane_warning:
        lines.append(f"> ⚠ pane query warning: {pane_warning}")
    return "\n".join(lines)


def build_pane_preview(
    session_name: str,
    window: dict[str, str],
    pane: dict[str, str],
    classify_pane_status_fn: Callable[[dict[str, str]], tuple[str, str]],
) -> str:
    process_name, status = classify_pane_status_fn(pane)
    lines = [
        f"# Session: {session_name}",
        "",
        "**backend:** tmux",
        f"**window:** {window['window_index']}:{window['window_name']}",
        f"**pane:** {pane['pane_index']}",
        "",
        f"- Process: {process_name}",
        f"- Status: {status}",
        f"- Directory: `{pane['pane_cwd'] or '—'}`",
        f"- Active: {'yes' if pane['pane_active'] else 'no'}",
    ]
    return "\n".join(lines)
