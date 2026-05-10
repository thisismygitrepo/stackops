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
from stackops.utils.schemas.layouts.layout_types import LayoutConfig


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
        if not tab["command"].strip():
            raise ValueError(f"Invalid command for tab '{tab['tabName']}': {tab['command']}")
        if not tab["startDir"].strip():
            raise ValueError(f"Invalid startDir for tab '{tab['tabName']}': {tab['startDir']}")


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


def _build_send_command_for_window(
    session_name: str,
    window_name: str,
    command: str,
    exit_mode: SessionExitMode,
) -> str:
    target = f"{session_name}:{window_name}"
    actual_command = command
    if exit_mode != "backToShell":
        actual_command = build_tmux_exit_mode_command(
            command=command,
            exit_mode=exit_mode,
        )
    return f"tmux send-keys -t {shell_quote(target)} {shell_quote(actual_command)} C-m"


def build_tmux_commands(
    layout_config: LayoutConfig,
    session_name: str,
    exit_mode: SessionExitMode,
) -> list[str]:
    validate_layout_config(layout_config)
    tabs = layout_config["layoutTabs"]
    first_tab = tabs[0]
    first_window = first_tab["tabName"]
    first_cwd = normalize_cwd(first_tab["startDir"])
    first_target = f"{session_name}:{first_window}"
    commands: list[str] = []
    commands_to_send: list[str] = []
    commands.append(
        f"tmux new-session -d -s {shell_quote(session_name)} -n {shell_quote(first_window)} -c {shell_quote(first_cwd)}"
    )
    if first_tab["command"].strip():
        commands_to_send.append(
            _build_send_command_for_window(
                session_name=session_name,
                window_name=first_window,
                command=first_tab["command"],
                exit_mode=exit_mode,
            )
        )
    for tab in tabs[1:]:
        commands.extend(
            _build_new_window_commands(
                session_name=session_name,
                window_name=tab["tabName"],
                cwd=normalize_cwd(tab["startDir"]),
            )
        )
        if tab["command"].strip():
            commands_to_send.append(
                _build_send_command_for_window(
                    session_name=session_name,
                    window_name=tab["tabName"],
                    command=tab["command"],
                    exit_mode=exit_mode,
                )
            )
    commands.append(f"tmux select-window -t {shell_quote(first_target)}")
    commands.extend(commands_to_send)
    return commands


def build_tmux_merge_commands(
    layout_config: LayoutConfig,
    session_name: str,
    on_conflict: TmuxMergeConflictAction,
    exit_mode: SessionExitMode,
) -> list[str]:
    validate_layout_config(layout_config)
    existing_window_names = list_tmux_window_names(session_name=session_name)
    first_target: str | None = None
    commands: list[str] = []
    commands_to_send: list[str] = []

    for tab in layout_config["layoutTabs"]:
        window_name = tab["tabName"]
        cwd = normalize_cwd(tab["startDir"])
        command = tab["command"]
        target = f"{session_name}:{window_name}"
        window_exists = window_name in existing_window_names

        match on_conflict:
            case "mergeSkip":
                if window_exists:
                    continue
                commands.extend(
                    _build_new_window_commands(
                        session_name=session_name,
                        window_name=window_name,
                        cwd=cwd,
                    )
                )
                if command.strip():
                    commands_to_send.append(
                        _build_send_command_for_window(
                            session_name=session_name,
                            window_name=window_name,
                            command=command,
                            exit_mode=exit_mode,
                        )
                    )
            case "mergeOverwrite":
                if window_exists:
                    commands.extend(
                        _build_replace_window_commands(
                            session_name=session_name,
                            window_name=window_name,
                            cwd=cwd,
                            reserved_window_names=existing_window_names,
                        )
                    )
                    if command.strip():
                        commands_to_send.append(
                            _build_send_command_for_window(
                                session_name=session_name,
                                window_name=window_name,
                                command=command,
                                exit_mode=exit_mode,
                            )
                        )
                else:
                    commands.extend(
                        _build_new_window_commands(
                            session_name=session_name,
                            window_name=window_name,
                            cwd=cwd,
                        )
                    )
                    if command.strip():
                        commands_to_send.append(
                            _build_send_command_for_window(
                                session_name=session_name,
                                window_name=window_name,
                                command=command,
                                exit_mode=exit_mode,
                            )
                        )
            case _:
                raise ValueError(f"Unsupported tmux merge policy: {on_conflict}")

        existing_window_names.add(window_name)
        if first_target is None:
            first_target = target

    if first_target is not None:
        commands.append(f"tmux select-window -t {shell_quote(first_target)}")
    commands.extend(commands_to_send)
    return commands


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
        )
    )