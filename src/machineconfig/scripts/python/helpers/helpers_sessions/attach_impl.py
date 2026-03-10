import re
import shlex
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Literal

from machineconfig.settings.zellij import layouts
from machineconfig.utils.installer_utils.installer_locator_utils import check_tool_exists
from machineconfig.utils.options import choose_from_options

root = layouts.__path__[0]
STANDARD = Path(root).joinpath("st2.kdl")

NEW_SESSION_LABEL = "NEW SESSION"
KILL_ALL_AND_NEW_LABEL = "KILL ALL SESSIONS & START NEW"
_KDL_ATTR_RE = re.compile(r'(\w+)=(?:"((?:\\.|[^"])*)"|([^\s{}]+))')
_ANSI_ESCAPE_RE = re.compile(
    r"(?:\x1B|\u001B|\033)\[[0-?]*[ -/]*[@-~]|\[[0-9;?]+[ -/]*[@-~]|\[m"
)


def strip_ansi_codes(text: str) -> str:
    return _ANSI_ESCAPE_RE.sub("", text)


def _natural_sort_key(text: str) -> list[int | str]:
    """Return a key for natural (human) sorting: numbers are compared numerically."""
    import re

    return [
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", text)
    ]


def _session_sort_key(raw_line: str) -> tuple[bool, list[int | str]]:
    """Sort key: active sessions first, then EXITED; within each group sort by session name (natural order)."""
    is_exited = "EXITED" in raw_line
    clean = strip_ansi_codes(raw_line)
    # Extract session name: everything before " [Created"
    name = clean.split(" [Created")[0].strip()
    return (is_exited, _natural_sort_key(name))


def _run_command(args: list[str], timeout: float = 5.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)


def _quote(value: str | Path) -> str:
    return shlex.quote(str(value))


def _zellij_session_name(raw_line: str) -> str:
    clean = strip_ansi_codes(raw_line)
    return clean.split(" [Created")[0].strip()


def _zellij_session_is_exited(raw_line: str) -> bool:
    return "EXITED" in strip_ansi_codes(raw_line)


def _zellij_session_is_current(raw_line: str) -> bool:
    return "(current)" in strip_ansi_codes(raw_line).casefold()


def _parse_kdl_attrs(line: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for key, quoted_value, bare_value in _KDL_ATTR_RE.findall(line):
        attrs[key] = (quoted_value or bare_value).replace('\\"', '"')
    return attrs


def _short_token(token: str) -> str:
    if token.startswith(("/", "~")):
        name = Path(token).name
        if name:
            return name
    return token


def _short_command(command: str | None, args: list[str]) -> str:
    tokens: list[str] = []
    if command:
        tokens.append(_short_token(command))
    tokens.extend(_short_token(arg) for arg in args[:3])
    if len(args) > 3:
        tokens.append("...")
    return " ".join(tokens).strip()


def _summarize_zellij_layout(layout_text: str) -> str | None:
    tabs: list[dict[str, object]] = []
    current_tab: dict[str, object] | None = None
    last_pane: dict[str, object] | None = None

    for raw_line in layout_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("//"):
            continue
        if line.startswith("tab "):
            attrs = _parse_kdl_attrs(line)
            current_tab = {"name": attrs.get("name") or f"Tab #{len(tabs) + 1}", "panes": []}
            tabs.append(current_tab)
            last_pane = None
            continue
        if current_tab is None:
            continue
        if line == "pane" or line.startswith("pane "):
            if "plugin location=" in line:
                last_pane = None
                continue
            attrs = _parse_kdl_attrs(line)
            is_actual_pane = line == "pane" or any(
                key in attrs for key in ("command", "name", "cwd")
            )
            if not is_actual_pane:
                last_pane = None
                continue
            pane = {
                "name": attrs.get("name"),
                "command": attrs.get("command"),
                "cwd": attrs.get("cwd"),
                "args": [],
            }
            panes = current_tab["panes"]
            assert isinstance(panes, list)
            panes.append(pane)
            last_pane = pane
            continue
        if line.startswith("args ") and last_pane is not None:
            try:
                last_pane["args"] = shlex.split(line[5:])
            except ValueError:
                last_pane["args"] = line[5:].split()

    if not tabs:
        return None

    lines = [f"tabs: {len(tabs)}"]
    for index, tab in enumerate(tabs, start=1):
        tab_name = str(tab["name"])
        panes = tab["panes"]
        assert isinstance(panes, list)
        lines.append(f"[{index}] {tab_name}")
        if not panes:
            lines.append("  - shell")
            continue
        for pane in panes:
            assert isinstance(pane, dict)
            pane_name = str(pane.get("name") or pane.get("command") or "shell")
            pane_command = pane.get("command")
            pane_args = pane.get("args")
            pane_cwd = pane.get("cwd")
            assert pane_command is None or isinstance(pane_command, str)
            assert pane_args is None or isinstance(pane_args, list)
            assert pane_cwd is None or isinstance(pane_cwd, str)
            detail = _short_command(pane_command, pane_args or [])
            if not detail:
                detail = "shell"
            if pane_cwd:
                detail = f"{detail} [{pane_cwd}]"
            if detail == pane_name:
                lines.append(f"  - {pane_name}")
            elif pane_name == "shell" and detail.startswith("shell"):
                lines.append(f"  - {detail}")
            else:
                lines.append(f"  - {pane_name}: {detail}")
    return "\n".join(lines)


def _find_latest_zellij_session_file(session_name: str) -> Path | None:
    cache_root = Path.home() / ".cache" / "zellij"
    candidates: list[Path] = []
    for file_name in ("session-layout.kdl", "session-metadata.kdl"):
        candidates.extend(
            path
            for path in cache_root.glob(f"*/session_info/{session_name}/{file_name}")
            if path.is_file()
        )
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _build_zellij_preview(raw_line: str) -> str:
    clean = strip_ansi_codes(raw_line).strip()
    session_name = _zellij_session_name(clean)
    state = "exited (attach to resurrect)" if _zellij_session_is_exited(clean) else "active"
    lines = [f"backend: zellij", f"session: {session_name}", f"state: {state}"]

    layout_result = _run_command(["zellij", "--session", session_name, "action", "dump-layout"])
    if layout_result.returncode == 0 and layout_result.stdout.strip():
        summary = _summarize_zellij_layout(layout_result.stdout)
        lines.append("preview: live layout")
        lines.append("")
        lines.append(summary or layout_result.stdout.strip())
        return "\n".join(lines)

    session_file = _find_latest_zellij_session_file(session_name)
    if session_file is not None:
        session_text = session_file.read_text(encoding="utf-8")
        summary = _summarize_zellij_layout(session_text)
        source_kind = "serialized layout" if session_file.name == "session-layout.kdl" else "serialized metadata"
        lines.append(f"preview: {source_kind}")
        lines.append("")
        lines.append(summary or session_text.strip() or "(empty session preview)")
        return "\n".join(lines)

    tabs_result = _run_command(["zellij", "--session", session_name, "action", "query-tab-names"])
    if tabs_result.returncode == 0 and tabs_result.stdout.strip():
        tab_names = [tab.strip() for tab in tabs_result.stdout.splitlines() if tab.strip()]
        lines.append("preview: live tab list")
        lines.append("")
        if tab_names:
            lines.append(f"tabs: {len(tab_names)}")
            lines.extend(f"- {tab_name}" for tab_name in tab_names)
        else:
            lines.append("(no tabs reported)")
        return "\n".join(lines)

    error_text = (layout_result.stderr or tabs_result.stderr or "No preview data available").strip()
    lines.append("")
    lines.append(error_text)
    return "\n".join(lines)


def _build_tmux_preview(session_name: str) -> str:
    lines = [f"backend: tmux", f"session: {session_name}"]
    windows_result = _run_command(
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
        lines.append("")
        lines.append(error_text)
        return "\n".join(lines)

    panes_result = _run_command(
        [
            "tmux",
            "list-panes",
            "-t",
            session_name,
            "-F",
            "#{window_index}\t#{pane_index}\t#{pane_title}\t#{pane_current_path}\t#{pane_current_command}\t#{?pane_active,active,}\t#{?pane_dead,dead,}",
        ]
    )

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
            panes_by_window[window_index].append(
                {
                    "pane_index": pane_index,
                    "pane_title": pane_title.strip(),
                    "pane_cwd": pane_cwd.strip(),
                    "pane_command": pane_command.strip(),
                    "pane_active": pane_active.strip(),
                    "pane_dead": pane_dead.strip(),
                }
            )

    lines.append(f"windows: {len(window_lines)}")
    lines.append("")
    for window_line in window_lines:
        parts = window_line.split("\t")
        while len(parts) < 4:
            parts.append("")
        window_index, window_name, window_panes, window_active = parts[:4]
        active_suffix = " (active)" if window_active.strip() else ""
        lines.append(f"[{window_index}] {window_name} ({window_panes} pane{'s' if window_panes != '1' else ''}){active_suffix}")
        window_panes_list = sorted(
            panes_by_window.get(window_index, []),
            key=lambda pane: int(pane["pane_index"]) if pane["pane_index"].isdigit() else pane["pane_index"],
        )
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


def _interactive_choose_with_preview(
    msg: str,
    options_to_preview_mapping: dict[str, str],
) -> str | None:
    if options_to_preview_mapping and check_tool_exists("tv"):
        from machineconfig.utils.options_utils.tv_options import choose_from_dict_with_preview

        try:
            result = choose_from_dict_with_preview(
                options_to_preview_mapping=options_to_preview_mapping,
                extension="txt",
                multi=False,
                preview_size_percent=70.0,
            )
            if isinstance(result, str) or result is None:
                return result
        except Exception:
            pass

    result = choose_from_options(
        msg=msg,
        multi=False,
        options=list(options_to_preview_mapping.keys()),
        tv=True,
        custom_input=False,
    )
    return result if isinstance(result, str) or result is None else None


def choose_zellij_session(
    name: str | None, new_session: bool, kill_all: bool
) -> tuple[str, str | None]:
    if name is not None:
        return ("run_script", f"zellij attach {_quote(name)}")
    if new_session:
        cmd = f"zellij --layout {_quote(STANDARD)}"
        if kill_all:
            cmd = f"zellij kill-all-sessions --yes\n{cmd}"
        return ("run_script", cmd)
    result = _run_command(["zellij", "list-sessions"])
    sessions = result.stdout.strip().splitlines() if result.returncode == 0 else []
    sessions = [s for s in sessions if s.strip()]
    sessions.sort(key=_session_sort_key)
    if any(_zellij_session_is_current(session) for session in sessions):
        return ("error", "Already in a Zellij session, avoiding nesting and exiting.")
    if len(sessions) == 0:
        return ("run_script", f"zellij --layout {_quote(STANDARD)}")
    if len(sessions) == 1:
        session_name = _zellij_session_name(sessions[0])
        return ("run_script", f"zellij attach {_quote(session_name)}")

    display_to_raw_session = {strip_ansi_codes(session): session for session in sessions}
    display_to_session = {
        display: _zellij_session_name(raw_session)
        for display, raw_session in display_to_raw_session.items()
    }
    options_to_preview_mapping = {
        display: _build_zellij_preview(raw_session)
        for display, raw_session in display_to_raw_session.items()
    }
    options_to_preview_mapping[NEW_SESSION_LABEL] = (
        "backend: zellij\n"
        "action: create a fresh session\n\n"
        f"zellij --layout {STANDARD}"
    )
    options_to_preview_mapping[KILL_ALL_AND_NEW_LABEL] = (
        "backend: zellij\n"
        "action: kill every existing session, then start a new one\n\n"
        "zellij kill-all-sessions --yes\n"
        f"zellij --layout {STANDARD}"
    )
    session_label = _interactive_choose_with_preview(
        msg="Choose a Zellij session to attach to:",
        options_to_preview_mapping=options_to_preview_mapping,
    )
    if session_label is None:
        return ("error", "No Zellij session selected.")
    if session_label == NEW_SESSION_LABEL:
        cmd = f"zellij --layout {_quote(STANDARD)}"
        if kill_all:
            cmd = f"zellij kill-all-sessions --yes\n{cmd}"
        return ("run_script", cmd)
    if session_label == KILL_ALL_AND_NEW_LABEL:
        return (
            "run_script",
            f"zellij kill-all-sessions --yes\nzellij --layout {_quote(STANDARD)}",
        )
    session_name = display_to_session.get(session_label)
    if session_name is None:
        return ("error", f"Unknown Zellij session selected: {session_label}")
    return ("run_script", f"zellij attach {_quote(session_name)}")


def choose_tmux_session(
    name: str | None, new_session: bool, kill_all: bool
) -> tuple[str, str | None]:
    if name is not None:
        return ("run_script", f"tmux attach -t {_quote(name)}")
    if new_session:
        cmd = "tmux new-session"
        if kill_all:
            cmd = f"tmux kill-server\n{cmd}"
        return ("run_script", cmd)
    result = _run_command(["tmux", "list-sessions", "-F", "#S"])
    sessions = result.stdout.strip().splitlines() if result.returncode == 0 else []
    sessions = [s for s in sessions if s.strip()]
    sessions.sort(
        key=lambda s: _natural_sort_key(
            strip_ansi_codes(s).split(" [Created")[0].strip()
        )
    )
    if len(sessions) == 0:
        return ("run_script", "tmux new-session")
    if len(sessions) == 1:
        return ("run_script", f"tmux attach -t {_quote(sessions[0])}")

    options_to_preview_mapping = {
        session_name: _build_tmux_preview(session_name) for session_name in sessions
    }
    options_to_preview_mapping[NEW_SESSION_LABEL] = (
        "backend: tmux\n"
        "action: create a fresh session\n\n"
        "tmux new-session"
    )
    options_to_preview_mapping[KILL_ALL_AND_NEW_LABEL] = (
        "backend: tmux\n"
        "action: kill the tmux server, then start a new session\n\n"
        "tmux kill-server\n"
        "tmux new-session"
    )
    session_name = _interactive_choose_with_preview(
        msg="Choose a tmux session to attach to:",
        options_to_preview_mapping=options_to_preview_mapping,
    )
    if session_name is None:
        return ("error", "No tmux session selected.")
    if session_name == NEW_SESSION_LABEL:
        cmd = "tmux new-session"
        if kill_all:
            cmd = f"tmux kill-server\n{cmd}"
        return ("run_script", cmd)
    if session_name == KILL_ALL_AND_NEW_LABEL:
        return ("run_script", "tmux kill-server\ntmux new-session")
    return ("run_script", f"tmux attach -t {_quote(session_name)}")


def choose_session(
    backend: Literal["zellij", "tmux"],
    name: str | None,
    new_session: bool,
    kill_all: bool,
) -> tuple[str, str | None]:
    match backend:
        case "zellij":
            return choose_zellij_session(
                name=name, new_session=new_session, kill_all=kill_all
            )
        case "tmux":
            return choose_tmux_session(
                name=name, new_session=new_session, kill_all=kill_all
            )
    raise ValueError(f"Unsupported backend: {backend}")


def get_session_tabs() -> list[tuple[str, str]]:
    result = _run_command(["zellij", "list-sessions"])
    sessions = result.stdout.strip().splitlines() if result.returncode == 0 else []
    sessions = [strip_ansi_codes(s) for s in sessions]
    active_sessions = [s for s in sessions if "EXITED" not in s]
    result: list[tuple[str, str]] = []
    for session_line in active_sessions:
        session_name = session_line.split(" [Created")[0].strip()
        tab_result = _run_command(
            ["zellij", "--session", session_name, "action", "query-tab-names"]
        )
        if tab_result.returncode != 0:
            continue
        tabs = [tab.strip() for tab in tab_result.stdout.splitlines() if tab.strip()]
        for tab in tabs:
            result.append((session_name, tab))
    return result
