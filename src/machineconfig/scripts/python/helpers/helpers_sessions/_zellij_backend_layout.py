import re
import shlex
from collections.abc import Sequence
from pathlib import Path
from typing import TypedDict


_KDL_ATTR_RE = re.compile(r'(\w+)=(?:"((?:\\.|[^"])*)"|([^\s{}]+))')


class LayoutPane(TypedDict):
    name: str | None
    command: str | None
    cwd: str | None
    args: list[str]


class LayoutTab(TypedDict):
    name: str
    panes: list[LayoutPane]


def parse_kdl_attrs(line: str) -> dict[str, str]:
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


def summarize_layout(layout_text: str) -> str | None:
    tabs: list[LayoutTab] = []
    current_tab: LayoutTab | None = None
    last_pane: LayoutPane | None = None

    for raw_line in layout_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("//"):
            continue
        if line.startswith("tab "):
            attrs = parse_kdl_attrs(line)
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
            attrs = parse_kdl_attrs(line)
            is_actual_pane = line == "pane" or any(key in attrs for key in ("command", "name", "cwd"))
            if not is_actual_pane:
                last_pane = None
                continue
            pane: LayoutPane = {
                "name": attrs.get("name"),
                "command": attrs.get("command"),
                "cwd": attrs.get("cwd"),
                "args": [],
            }
            panes = current_tab["panes"]
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
        lines.append(f"[{index}] {tab_name}")
        if not panes:
            lines.append("  - shell")
            continue
        for pane_item in panes:
            pane_name = str(pane_item.get("name") or pane_item.get("command") or "shell")
            pane_command = pane_item.get("command")
            pane_args = pane_item.get("args")
            pane_cwd = pane_item.get("cwd")
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
