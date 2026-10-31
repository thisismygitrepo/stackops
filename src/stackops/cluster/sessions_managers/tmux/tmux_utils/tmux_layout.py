#!/usr/bin/env python3
import os
import subprocess
from typing import Literal

from stackops.cluster.sessions_managers.session_exit_mode import (
    SessionExitMode,
    build_tmux_exit_mode_command,
)
from stackops.cluster.sessions_managers.tmux.tmux_utils.tmux_common import (
    generate_random_suffix,
    normalize_cwd,
    shell_quote,
)
from stackops.utils.schemas.layouts.layout_constants import DEFAULT_TAB_ARRANGEMENT
from stackops.utils.schemas.layouts.layout_types import LayoutConfig, TabConfig


TmuxMergeConflictAction = Literal[
    "mergeOverwrite",
    "mergeSkip",
]


def validate_layout_config(layout_config: LayoutConfig) -> None:
    if not layout_config["layoutTabs"]:
        raise ValueError("Layout must contain at least one tab")
    for tab in layout_config["layoutTabs"]:
        if not tab["tabName"].strip():
            raise ValueError(f"Invalid tab name: {tab['tabName']}")
        if not tab["panes"]:
            raise ValueError(f"Tab '{tab['tabName']}' must contain at least one pane")
        for pane in tab["panes"]:
            if not pane["paneName"].strip():
                raise ValueError(f"Invalid pane name in tab '{tab['tabName']}': {pane['paneName']}")
            if not pane["command"].strip():
                raise ValueError(f"Invalid command for pane '{pane['paneName']}' in tab '{tab['tabName']}': {pane['command']}")
            if not pane["startDir"].strip():
                raise ValueError(f"Invalid startDir for pane '{pane['paneName']}' in tab '{tab['tabName']}': {pane['startDir']}")


def list_tmux_window_names(session_name: str) -> set[str]:
    try:
        result = subprocess.run(
            ["tmux", "list-windows", "-t", session_name, "-F", "#{window_name}"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except FileNotFoundError:
        return set()
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"Timed out while listing tmux windows for session '{session_name}'."
        ) from exc

    if result.returncode != 0:
        stderr = (result.stderr or "").strip().lower()
        if "can't find session" in stderr or "no server running" in stderr:
            return set()
        detail = (result.stderr or result.stdout or "Unknown error").strip()
        raise RuntimeError(
            f"Failed to list tmux windows for session '{session_name}': {detail}"
        )
    return {line.strip() for line in (result.stdout or "").splitlines() if line.strip()}


def _build_new_window_commands(
    session_name: str,
    window_name: str,
    cwd: str,
) -> list[str]:
    session_target = f"{session_name}:"
    return [
        f"tmux new-window -t {shell_quote(session_target)} -n {shell_quote(window_name)} -c {shell_quote(cwd)}",
    ]


def _build_temporary_window_name(
    window_name: str,
    reserved_window_names: set[str],
) -> str:
    while True:
        candidate_name = (
            f"{window_name}__stackops_replace__"
            f"{generate_random_suffix(length=8)}"
        )
        if candidate_name not in reserved_window_names:
            reserved_window_names.add(candidate_name)
            return candidate_name


def _build_replace_window_commands(
    session_name: str,
    window_name: str,
    cwd: str,
    reserved_window_names: set[str],
) -> list[str]:
    temp_window_name = _build_temporary_window_name(
        window_name=window_name,
        reserved_window_names=reserved_window_names,
    )
    session_target = f"{session_name}:"
    target = f"{session_name}:{window_name}"
    temp_target = f"{session_name}:{temp_window_name}"
    return [
        f"tmux new-window -t {shell_quote(session_target)} -n {shell_quote(temp_window_name)} -c {shell_quote(cwd)}",
        f"tmux kill-window -t {shell_quote(target)}",
        f"tmux rename-window -t {shell_quote(temp_target)} {shell_quote(window_name)}",
    ]


def _build_tab_pane_commands(
    session_name: str,
    tab: TabConfig,
    exit_mode: SessionExitMode,
) -> list[str]:
    window_target = shell_quote(f"{session_name}:{tab['tabName']}")
    commands: list[str] = []
    for pane_index, pane in enumerate(tab["panes"]):
        if pane_index > 0:
            commands.append(
                f"tmux split-window -t {window_target} -c {shell_quote(normalize_cwd(pane['startDir']))}"
            )
        commands.append(f"tmux select-pane -t {window_target} -T {shell_quote(pane['paneName'])}")
        actual_command = pane["command"]
        if exit_mode != "backToShell":
            actual_command = build_tmux_exit_mode_command(
                command=actual_command,
                exit_mode=exit_mode,
            )
        commands.append(f"tmux send-keys -t {window_target} {shell_quote(actual_command)} C-m")
    if len(tab["panes"]) > 1:
        match tab.get("arrangement", DEFAULT_TAB_ARRANGEMENT):
            case "columns":
                tmux_layout = "even-horizontal"
            case "rows":
                tmux_layout = "even-vertical"
            case "grid":
                tmux_layout = "tiled"
        commands.append(f"tmux select-layout -t {window_target} {tmux_layout}")
        first_pane_target = shell_quote(f"{session_name}:{tab['tabName']}.{{top-left}}")
        commands.append(f"tmux select-pane -t {first_pane_target}")
    return commands


def build_tmux_new_window_tab_commands(
    session_name: str,
    tab: TabConfig,
    exit_mode: SessionExitMode,
) -> list[str]:
    return [
        *_build_new_window_commands(
            session_name=session_name,
            window_name=tab["tabName"],
            cwd=normalize_cwd(tab["panes"][0]["startDir"]),
        ),
        *_build_tab_pane_commands(session_name=session_name, tab=tab, exit_mode=exit_mode),
    ]


def build_tmux_commands(
    layout_config: LayoutConfig,
    session_name: str,
    exit_mode: SessionExitMode,
) -> list[str]:
    validate_layout_config(layout_config)
    tabs = layout_config["layoutTabs"]
    first_window = tabs[0]["tabName"]
    commands: list[str] = []
    first_cwd = normalize_cwd(tabs[0]["panes"][0]["startDir"])
    commands.append(
        f"tmux new-session -d -s {shell_quote(session_name)} -n {shell_quote(first_window)} -c {shell_quote(first_cwd)}"
    )
    commands.extend(_build_tab_pane_commands(session_name=session_name, tab=tabs[0], exit_mode=exit_mode))
    for tab in tabs[1:]:
        commands.extend(build_tmux_new_window_tab_commands(session_name=session_name, tab=tab, exit_mode=exit_mode))
    commands.append(f"tmux select-window -t {shell_quote(f'{session_name}:{first_window}')}")
    return commands


def build_tmux_merge_commands(
    layout_config: LayoutConfig,
    session_name: str,
    on_conflict: TmuxMergeConflictAction,
    exit_mode: SessionExitMode,
) -> tuple[list[str], list[TabConfig]]:
    validate_layout_config(layout_config)
    existing_window_names = list_tmux_window_names(session_name=session_name)
    first_target: str | None = None
    commands: list[str] = []
    launched_tabs: list[TabConfig] = []

    for tab in layout_config["layoutTabs"]:
        window_name = tab["tabName"]
        window_exists = window_name in existing_window_names

        match on_conflict:
            case "mergeSkip":
                if window_exists:
                    continue
                commands.extend(
                    build_tmux_new_window_tab_commands(session_name=session_name, tab=tab, exit_mode=exit_mode)
                )
            case "mergeOverwrite":
                if window_exists:
                    commands.extend(
                        _build_replace_window_commands(
                            session_name=session_name,
                            window_name=window_name,
                            cwd=normalize_cwd(tab["panes"][0]["startDir"]),
                            reserved_window_names=existing_window_names,
                        )
                    )
                    commands.extend(_build_tab_pane_commands(session_name=session_name, tab=tab, exit_mode=exit_mode))
                else:
                    commands.extend(
                        build_tmux_new_window_tab_commands(session_name=session_name, tab=tab, exit_mode=exit_mode)
                    )
            case _:
                raise ValueError(f"Unsupported tmux merge policy: {on_conflict}")

        launched_tabs.append(tab)
        existing_window_names.add(window_name)
        if first_target is None:
            first_target = f"{session_name}:{window_name}"

    if first_target is not None:
        commands.append(f"tmux select-window -t {shell_quote(first_target)}")
    return commands, launched_tabs


def build_tmux_script(
    layout_config: LayoutConfig,
    session_name: str,
    exit_mode: SessionExitMode,
) -> str:
    return build_tmux_script_from_commands(
        build_tmux_commands(
            layout_config=layout_config,
            session_name=session_name,
            exit_mode=exit_mode,
        )
    )


def build_tmux_script_from_commands(commands: list[str]) -> str:
    if os.name == "nt":
        script_lines = ["$ErrorActionPreference = 'Stop'"]
    else:
        script_lines = ["#!/usr/bin/env bash", "set -e"]
    script_lines.extend(commands)
    return "\n".join(script_lines) + "\n"


def build_tmux_merge_script(
    layout_config: LayoutConfig,
    session_name: str,
    on_conflict: TmuxMergeConflictAction,
    exit_mode: SessionExitMode,
) -> str:
    return build_tmux_script_from_commands(
        build_tmux_merge_commands(
            layout_config=layout_config,
            session_name=session_name,
            on_conflict=on_conflict,
            exit_mode=exit_mode,
        )[0]
    )