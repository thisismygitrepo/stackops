import re
import shlex
from collections.abc import Sequence
from pathlib import Path

from machineconfig.scripts.python.helpers.helpers_sessions.attach_impl import (
    KILL_ALL_AND_NEW_LABEL,
    NEW_SESSION_LABEL,
    STANDARD,
    interactive_choose_with_preview,
    natural_sort_key,
    quote,
    run_command,
    strip_ansi_codes,
)

_KDL_ATTR_RE = re.compile(r'(\w+)=(?:"((?:\\.|[^"])*)"|([^\s{}]+))')


def _session_sort_key(raw_line: str) -> tuple[bool, list[int | str]]:
    is_exited = "EXITED" in raw_line
    clean = strip_ansi_codes(raw_line)
    name = clean.split(" [Created")[0].strip()
    return (is_exited, natural_sort_key(name))


def _session_name(raw_line: str) -> str:
    return strip_ansi_codes(raw_line).split(" [Created")[0].strip()


def _session_is_exited(raw_line: str) -> bool:
    return "EXITED" in strip_ansi_codes(raw_line)


def _session_is_current(raw_line: str) -> bool:
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


def _short_command(command: str | None, args: Sequence[str]) -> str:
    tokens: list[str] = []
    if command:
        tokens.append(_short_token(command))
    tokens.extend(_short_token(arg) for arg in args[:3])
    if len(args) > 3:
        tokens.append("...")
    return " ".join(tokens).strip()


def _summarize_layout(layout_text: str) -> str | None:
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
            is_actual_pane = line == "pane" or any(key in attrs for key in ("command", "name", "cwd"))
            if not is_actual_pane:
                last_pane = None
                continue
            pane: dict[str, object] = {"name": attrs.get("name"), "command": attrs.get("command"), "cwd": attrs.get("cwd"), "args": []}
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

    lines: list[str] = [f"tabs: {len(tabs)}"]
    for index, tab in enumerate(tabs, start=1):
        tab_name = str(tab["name"])
        panes = tab["panes"]
        assert isinstance(panes, list)
        lines.append(f"[{index}] {tab_name}")
        if not panes:
            lines.append("  - shell")
            continue
        for pane_item in panes:
            assert isinstance(pane_item, dict)
            pane_name = str(pane_item.get("name") or pane_item.get("command") or "shell")
            pane_command = pane_item.get("command")
            pane_args = pane_item.get("args")
            pane_cwd = pane_item.get("cwd")
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


def _find_latest_session_file(session_name: str) -> Path | None:
    cache_root = Path.home() / ".cache" / "zellij"
    candidates: list[Path] = []
    for file_name in ("session-layout.kdl", "session-metadata.kdl"):
        candidates.extend(path for path in cache_root.glob(f"*/session_info/{session_name}/{file_name}") if path.is_file())
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _build_preview(raw_line: str) -> str:
    clean = strip_ansi_codes(raw_line).strip()
    session_name = _session_name(clean)
    state = "exited (attach to resurrect)" if _session_is_exited(clean) else "active"
    lines = ["backend: zellij", f"session: {session_name}", f"state: {state}"]

    layout_result = run_command(["zellij", "--session", session_name, "action", "dump-layout"])
    if layout_result.returncode == 0 and layout_result.stdout.strip():
        summary = _summarize_layout(layout_result.stdout)
        lines.append("preview: live layout")
        lines.append("")
        lines.append(summary or layout_result.stdout.strip())
        return "\n".join(lines)

    session_file = _find_latest_session_file(session_name)
    if session_file is not None:
        session_text = session_file.read_text(encoding="utf-8")
        summary = _summarize_layout(session_text)
        source_kind = "serialized layout" if session_file.name == "session-layout.kdl" else "serialized metadata"
        lines.append(f"preview: {source_kind}")
        lines.append("")
        lines.append(summary or session_text.strip() or "(empty session preview)")
        return "\n".join(lines)

    tabs_result = run_command(["zellij", "--session", session_name, "action", "query-tab-names"])
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


def choose_session(name: str | None, new_session: bool, kill_all: bool) -> tuple[str, str | None]:
    if name is not None:
        return ("run_script", f"zellij attach {quote(name)}")
    if new_session:
        cmd = f"zellij --layout {quote(STANDARD)}"
        if kill_all:
            cmd = f"zellij kill-all-sessions --yes\n{cmd}"
        return ("run_script", cmd)
    result = run_command(["zellij", "list-sessions"])
    sessions = result.stdout.strip().splitlines() if result.returncode == 0 else []
    sessions = [s for s in sessions if s.strip()]
    sessions.sort(key=_session_sort_key)
    if any(_session_is_current(session) for session in sessions):
        return ("error", "Already in a Zellij session, avoiding nesting and exiting.")
    if len(sessions) == 0:
        return ("run_script", f"zellij --layout {quote(STANDARD)}")
    if len(sessions) == 1:
        session_name = _session_name(sessions[0])
        return ("run_script", f"zellij attach {quote(session_name)}")

    display_to_raw_session = {strip_ansi_codes(session): session for session in sessions}
    display_to_session = {display: _session_name(raw_session) for display, raw_session in display_to_raw_session.items()}
    options_to_preview_mapping = {display: _build_preview(raw_session) for display, raw_session in display_to_raw_session.items()}
    options_to_preview_mapping[NEW_SESSION_LABEL] = f"backend: zellij\naction: create a fresh session\n\nzellij --layout {STANDARD}"
    options_to_preview_mapping[KILL_ALL_AND_NEW_LABEL] = f"backend: zellij\naction: kill every existing session, then start a new one\n\nzellij kill-all-sessions --yes\nzellij --layout {STANDARD}"
    session_label = interactive_choose_with_preview(msg="Choose a Zellij session to attach to:", options_to_preview_mapping=options_to_preview_mapping)
    if session_label is None:
        return ("error", "No Zellij session selected.")
    if session_label == NEW_SESSION_LABEL:
        cmd = f"zellij --layout {quote(STANDARD)}"
        if kill_all:
            cmd = f"zellij kill-all-sessions --yes\n{cmd}"
        return ("run_script", cmd)
    if session_label == KILL_ALL_AND_NEW_LABEL:
        return ("run_script", f"zellij kill-all-sessions --yes\nzellij --layout {quote(STANDARD)}")
    session_name = display_to_session.get(session_label)
    if session_name is None:
        return ("error", f"Unknown Zellij session selected: {session_label}")
    return ("run_script", f"zellij attach {quote(session_name)}")


def get_session_tabs() -> list[tuple[str, str]]:
    result = run_command(["zellij", "list-sessions"])
    sessions = result.stdout.strip().splitlines() if result.returncode == 0 else []
    sessions = [strip_ansi_codes(s) for s in sessions]
    active_sessions = [s for s in sessions if "EXITED" not in s]
    tabs: list[tuple[str, str]] = []
    for session_line in active_sessions:
        session_name = session_line.split(" [Created")[0].strip()
        tab_result = run_command(["zellij", "--session", session_name, "action", "query-tab-names"])
        if tab_result.returncode != 0:
            continue
        tab_names = [tab.strip() for tab in tab_result.stdout.splitlines() if tab.strip()]
        for tab in tab_names:
            tabs.append((session_name, tab))
    return tabs
