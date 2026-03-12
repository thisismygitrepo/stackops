from pathlib import Path
from typing import Callable, TypeAlias, cast

from machineconfig.scripts.python.helpers.helpers_sessions._zellij_backend_focus import (
    focus_path_to_pane,
    selectable_panes_for_tab,
)
from machineconfig.scripts.python.helpers.helpers_sessions._zellij_backend_metadata import pane_title

_SessionMetadata: TypeAlias = tuple[list[dict[str, object]], list[dict[str, object]]]
_ReadSessionMetadataFn: TypeAlias = Callable[[str], _SessionMetadata | None]


def new_session_script(standard_layout: Path, quote_fn: Callable[[str | Path], str], kill_all: bool) -> str:
    command = f"zellij --layout {quote_fn(standard_layout)}"
    if kill_all:
        command = f"zellij kill-all-sessions --yes\n{command}"
    return command


def attach_script_for_target(
    session_name: str,
    quote_fn: Callable[[str | Path], str],
    tab_name: str | None = None,
    pane_focus_commands: list[str] | None = None,
) -> str:
    commands: list[str] = []
    if tab_name:
        commands.append(f"zellij --session {quote_fn(session_name)} action go-to-tab-name {quote_fn(tab_name)}")
    for direction in pane_focus_commands or []:
        commands.append(f"zellij --session {quote_fn(session_name)} action move-focus {direction}")
    commands.append(f"zellij attach {quote_fn(session_name)}")
    return "\n".join(commands)


def kill_script_for_target(
    session_name: str,
    quote_fn: Callable[[str | Path], str],
    tab_name: str | None = None,
    pane_focus_commands: list[str] | None = None,
    kill_pane: bool = False,
) -> str:
    if tab_name is None:
        return f"zellij delete-session --force {quote_fn(session_name)}"

    commands: list[str] = [f"zellij --session {quote_fn(session_name)} action go-to-tab-name {quote_fn(tab_name)}"]
    if kill_pane:
        if pane_focus_commands is None:
            raise ValueError("pane_focus_commands must be provided when kill_pane is True")
        for direction in pane_focus_commands:
            commands.append(f"zellij --session {quote_fn(session_name)} action move-focus {direction}")
        commands.append(f"zellij --session {quote_fn(session_name)} action close-pane")
        return "\n".join(commands)

    commands.append(f"zellij --session {quote_fn(session_name)} action close-tab")
    return "\n".join(commands)


def _build_tab_preview(
    session_name: str,
    tab: dict[str, object],
    panes: list[dict[str, object]],
) -> str:
    tab_name = str(tab.get("name") or "Tab")
    tab_position = cast(int, tab.get("position", 0)) + 1
    lines = [
        "backend: zellij",
        f"session: {session_name}",
        f"tab: [{tab_position}] {tab_name}",
        f"active: {'yes' if tab.get('active') else 'no'}",
        "",
    ]
    if not panes:
        lines.append("panes: 0")
        return "\n".join(lines)
    lines.append(f"panes: {len(panes)}")
    for pane in panes:
        markers: list[str] = []
        if pane.get("is_focused"):
            markers.append("focused")
        if pane.get("is_floating"):
            markers.append("floating")
        marker_text = f" ({', '.join(markers)})" if markers else ""
        lines.append(f"- {pane_title(pane)}{marker_text}")
    return "\n".join(lines)


def _build_pane_preview(
    session_name: str,
    tab: dict[str, object],
    pane: dict[str, object],
    focus_path: list[str] | None,
) -> str:
    tab_name = str(tab.get("name") or "Tab")
    tab_position = cast(int, tab.get("position", 0)) + 1
    pane_x = cast(int, pane.get("pane_x", 0))
    pane_y = cast(int, pane.get("pane_y", 0))
    pane_columns = cast(int, pane.get("pane_columns", 0))
    pane_rows = cast(int, pane.get("pane_rows", 0))
    if focus_path is None:
        focus_text = "tab focus only"
    elif not focus_path:
        focus_text = "already focused in this tab"
    else:
        focus_text = "move-focus " + " -> ".join(focus_path)
    lines = [
        "backend: zellij",
        f"session: {session_name}",
        f"tab: [{tab_position}] {tab_name}",
        f"pane: {pane_title(pane)}",
        f"geometry: {pane_columns}x{pane_rows} @ ({pane_x}, {pane_y})",
        f"floating: {'yes' if pane.get('is_floating') else 'no'}",
        f"focus plan: {focus_text}",
    ]
    return "\n".join(lines)


def build_window_target_options(
    active_sessions: list[str],
    read_session_metadata_fn: _ReadSessionMetadataFn,
    get_live_tab_names_fn: Callable[[str], list[str]],
    quote_fn: Callable[[str | Path], str],
) -> tuple[dict[str, str], dict[str, str]]:
    options_to_scripts: dict[str, str] = {}
    options_to_previews: dict[str, str] = {}

    for session_name in active_sessions:
        metadata = read_session_metadata_fn(session_name)
        if metadata is not None:
            tabs, panes = metadata
            for tab in tabs:
                tab_name = str(tab.get("name") or "Tab")
                tab_position = cast(int, tab.get("position", 0))
                display_prefix = f"[{session_name}] {tab_position + 1}:{tab_name}"
                if tab.get("active"):
                    display_prefix += " *"
                tab_panes = selectable_panes_for_tab(panes, tab_position)
                options_to_scripts[display_prefix] = attach_script_for_target(
                    session_name=session_name,
                    quote_fn=quote_fn,
                    tab_name=tab_name,
                )
                options_to_previews[display_prefix] = _build_tab_preview(
                    session_name=session_name,
                    tab=tab,
                    panes=tab_panes,
                )
                for pane in tab_panes:
                    pane_focus_path = focus_path_to_pane(tab_panes, pane)
                    pane_label = f"[{session_name}] {tab_position + 1}:{tab_name} / {pane_title(pane)}"
                    if pane.get("is_focused"):
                        pane_label += " *"
                    options_to_scripts[pane_label] = attach_script_for_target(
                        session_name=session_name,
                        quote_fn=quote_fn,
                        tab_name=tab_name,
                        pane_focus_commands=pane_focus_path or [],
                    )
                    options_to_previews[pane_label] = _build_pane_preview(
                        session_name=session_name,
                        tab=tab,
                        pane=pane,
                        focus_path=pane_focus_path,
                    )
            continue

        live_tab_names = get_live_tab_names_fn(session_name)
        for index, tab_name in enumerate(live_tab_names, start=1):
            label = f"[{session_name}] {index}:{tab_name}"
            options_to_scripts[label] = attach_script_for_target(
                session_name=session_name,
                quote_fn=quote_fn,
                tab_name=tab_name,
            )
            options_to_previews[label] = "\n".join(
                [
                    "backend: zellij",
                    f"session: {session_name}",
                    f"tab: [{index}] {tab_name}",
                    "",
                    "Pane metadata is unavailable for this session.",
                ]
            )
    return (options_to_scripts, options_to_previews)


def build_kill_target_options(
    active_sessions: list[str],
    read_session_metadata_fn: _ReadSessionMetadataFn,
    get_live_tab_names_fn: Callable[[str], list[str]],
    quote_fn: Callable[[str | Path], str],
) -> tuple[dict[str, str], dict[str, str]]:
    options_to_scripts: dict[str, str] = {}
    options_to_previews: dict[str, str] = {}

    for session_name in active_sessions:
        metadata = read_session_metadata_fn(session_name)
        if metadata is not None:
            tabs, panes = metadata
            for tab in tabs:
                tab_name = str(tab.get("name") or "Tab")
                tab_position = cast(int, tab.get("position", 0))
                display_prefix = f"[{session_name}] {tab_position + 1}:{tab_name}"
                if tab.get("active"):
                    display_prefix += " *"
                tab_panes = selectable_panes_for_tab(panes, tab_position)
                options_to_scripts[display_prefix] = kill_script_for_target(
                    session_name=session_name,
                    quote_fn=quote_fn,
                    tab_name=tab_name,
                )
                options_to_previews[display_prefix] = _build_tab_preview(
                    session_name=session_name,
                    tab=tab,
                    panes=tab_panes,
                )
                for pane in tab_panes:
                    pane_focus_path = focus_path_to_pane(tab_panes, pane)
                    if pane_focus_path is None:
                        continue
                    pane_label = f"[{session_name}] {tab_position + 1}:{tab_name} / {pane_title(pane)}"
                    if pane.get("is_focused"):
                        pane_label += " *"
                    options_to_scripts[pane_label] = kill_script_for_target(
                        session_name=session_name,
                        quote_fn=quote_fn,
                        tab_name=tab_name,
                        pane_focus_commands=pane_focus_path,
                        kill_pane=True,
                    )
                    options_to_previews[pane_label] = _build_pane_preview(
                        session_name=session_name,
                        tab=tab,
                        pane=pane,
                        focus_path=pane_focus_path,
                    )
            continue

        live_tab_names = get_live_tab_names_fn(session_name)
        for index, tab_name in enumerate(live_tab_names, start=1):
            label = f"[{session_name}] {index}:{tab_name}"
            options_to_scripts[label] = kill_script_for_target(
                session_name=session_name,
                quote_fn=quote_fn,
                tab_name=tab_name,
            )
            options_to_previews[label] = "\n".join(
                [
                    "backend: zellij",
                    f"session: {session_name}",
                    f"tab: [{index}] {tab_name}",
                    "",
                    "Pane metadata is unavailable for this session.",
                ]
            )
    return (options_to_scripts, options_to_previews)
