import re
from collections import defaultdict
from pathlib import Path
from subprocess import CompletedProcess
from typing import Callable


def find_latest_session_info_file(session_name: str, *file_names: str) -> Path | None:
    cache_root = Path.home() / ".cache" / "zellij"
    candidates: list[Path] = []
    for file_name in file_names:
        candidates.extend(path for path in cache_root.glob(f"*/session_info/{session_name}/{file_name}") if path.is_file())
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def find_latest_session_file(session_name: str) -> Path | None:
    return find_latest_session_info_file(session_name, "session-layout.kdl", "session-metadata.kdl")


def _parse_metadata_scalar(raw_value: str) -> str | int | bool:
    value = raw_value.strip()
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1].replace('\\"', '"')
    if value == "true":
        return True
    if value == "false":
        return False
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def _parse_session_metadata(metadata_text: str) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    tabs: list[dict[str, object]] = []
    panes: list[dict[str, object]] = []
    stack: list[str] = []
    current_tab: dict[str, object] | None = None
    current_pane: dict[str, object] | None = None

    for raw_line in metadata_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("//"):
            continue
        if line.endswith("{"):
            token = line[:-1].strip().split()[0]
            stack.append(token)
            if stack[-2:] == ["tabs", "tab"]:
                current_tab = {}
            elif stack[-2:] == ["panes", "pane"]:
                current_pane = {}
            continue
        if line == "}":
            if stack[-2:] == ["tabs", "tab"] and current_tab is not None:
                tabs.append(current_tab)
                current_tab = None
            elif stack[-2:] == ["panes", "pane"] and current_pane is not None:
                panes.append(current_pane)
                current_pane = None
            if stack:
                stack.pop()
            continue
        key, _, raw_value = line.partition(" ")
        if not raw_value:
            continue
        if stack and stack[-1] == "tab" and current_tab is not None:
            current_tab[key] = _parse_metadata_scalar(raw_value)
        elif stack and stack[-1] == "pane" and current_pane is not None:
            current_pane[key] = _parse_metadata_scalar(raw_value)

    return (tabs, panes)


def _tab_sort_key(tab: dict[str, object]) -> int:
    position = tab.get("position", 0)
    return int(position) if isinstance(position, int) else 0


def _pane_sort_key(pane: dict[str, object]) -> tuple[int, int, int, int]:
    tab_position = pane.get("tab_position", 0)
    pane_y = pane.get("pane_y", 0)
    pane_x = pane.get("pane_x", 0)
    pane_id = pane.get("id", 0)
    return (
        int(tab_position) if isinstance(tab_position, int) else 0,
        int(pane_y) if isinstance(pane_y, int) else 0,
        int(pane_x) if isinstance(pane_x, int) else 0,
        int(pane_id) if isinstance(pane_id, int) else 0,
    )


def read_session_metadata(session_name: str) -> tuple[list[dict[str, object]], list[dict[str, object]]] | None:
    session_file = find_latest_session_info_file(session_name, "session-metadata.kdl")
    if session_file is None:
        return None
    try:
        metadata_text = session_file.read_text(encoding="utf-8")
    except OSError:
        return None
    tabs, panes = _parse_session_metadata(metadata_text)
    tabs.sort(key=_tab_sort_key)
    panes.sort(key=_pane_sort_key)
    return (tabs, panes)


def pane_title(pane: dict[str, object]) -> str:
    title = pane.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()
    pane_id = pane.get("id")
    return f"Pane #{pane_id}" if pane_id is not None else "Pane"


def build_metadata_summary(
    tabs: list[dict[str, object]],
    panes: list[dict[str, object]],
) -> str | None:
    if not tabs:
        return None

    panes_by_tab: dict[int, list[dict[str, object]]] = defaultdict(list)
    for pane in panes:
        tab_position = pane.get("tab_position")
        if isinstance(tab_position, int):
            panes_by_tab[tab_position].append(pane)

    lines: list[str] = [f"tabs: {len(tabs)}"]
    for index, tab in enumerate(tabs, start=1):
        position = tab.get("position", index - 1)
        tab_name = str(tab.get("name") or f"Tab #{index}")
        active = " *" if tab.get("active") else ""
        lines.append(f"[{index}] {tab_name}{active}")
        selectable_panes = [
            pane
            for pane in panes_by_tab.get(int(position) if isinstance(position, int) else index - 1, [])
            if pane.get("is_selectable") and not pane.get("is_plugin")
        ]
        if not selectable_panes:
            lines.append("  - shell")
            continue
        for pane in selectable_panes:
            markers: list[str] = []
            if pane.get("is_focused"):
                markers.append("focused")
            if pane.get("is_floating"):
                markers.append("floating")
            marker_text = f" ({', '.join(markers)})" if markers else ""
            lines.append(f"  - {pane_title(pane)}{marker_text}")
    return "\n".join(lines)


def get_live_tab_names(
    session_name: str,
    run_command_fn: Callable[..., CompletedProcess[str]],
) -> list[str]:
    tabs_result = run_command_fn(["zellij", "--session", session_name, "action", "query-tab-names"])
    if tabs_result.returncode != 0:
        return []
    return [tab.strip() for tab in tabs_result.stdout.splitlines() if tab.strip()]
