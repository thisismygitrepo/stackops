#!/usr/bin/env python3
from pathlib import Path
import random
import string
import subprocess
import shlex
from typing import Literal, NotRequired, TypedDict

from machineconfig.utils.schemas.layouts.layout_types import LayoutConfig, TabConfig
from machineconfig.cluster.sessions_managers.zellij.zellij_utils.monitoring_types import CommandStatus


class TmuxSessionStatus(TypedDict):
    tmux_running: bool
    session_exists: bool
    session_name: str
    all_sessions: list[str]
    error: NotRequired[str]


TmuxMergeConflictAction = Literal[
    "mergeNewWindowsOverwriteMatchingWindows",
    "mergeNewWindowsSkipMatchingWindows",
]


def generate_random_suffix(length: int) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def normalize_cwd(cwd: str) -> str:
    normalized = cwd.replace("$HOME", str(Path.home()))
    return str(Path(normalized).expanduser())


def shell_quote(value: str) -> str:
    return shlex.quote(value)


def build_tmux_attach_or_switch_command(session_name: str) -> str:
    quoted_session_name = shell_quote(session_name)
    return (
        'if [ -n "${TMUX:-}" ]; then '
        f"tmux switch-client -t {quoted_session_name}; "
        "else "
        f"tmux attach -t {quoted_session_name}; "
        "fi"
    )


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
    command: str,
) -> list[str]:
    session_target = f"{session_name}:"
    target = f"{session_name}:{window_name}"
    return [
        f"tmux new-window -t {shell_quote(session_target)} -n {shell_quote(window_name)} -c {shell_quote(cwd)}",
        f"tmux send-keys -t {shell_quote(target)} {shell_quote(command)} C-m",
    ]


def _build_temporary_window_name(
    window_name: str,
    reserved_window_names: set[str],
) -> str:
    while True:
        candidate_name = (
            f"{window_name}__machineconfig_replace__"
            f"{generate_random_suffix(length=8)}"
        )
        if candidate_name not in reserved_window_names:
            reserved_window_names.add(candidate_name)
            return candidate_name


def _build_replace_window_commands(
    session_name: str,
    window_name: str,
    cwd: str,
    command: str,
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
        f"tmux send-keys -t {shell_quote(temp_target)} {shell_quote(command)} C-m",
        f"tmux kill-window -t {shell_quote(target)}",
        f"tmux rename-window -t {shell_quote(temp_target)} {shell_quote(window_name)}",
    ]


def build_tmux_commands(layout_config: LayoutConfig, session_name: str) -> list[str]:
    validate_layout_config(layout_config)
    tabs = layout_config["layoutTabs"]
    first_tab = tabs[0]
    first_window = first_tab["tabName"]
    first_cwd = normalize_cwd(first_tab["startDir"])
    first_target = f"{session_name}:{first_window}"
    commands: list[str] = []
    session_target = f"{session_name}:"
    commands.append(
        f"tmux new-session -d -s {shell_quote(session_name)} -n {shell_quote(first_window)} -c {shell_quote(first_cwd)}"
    )
    if first_tab["command"].strip():
        commands.append(
            f"tmux send-keys -t {shell_quote(first_target)} {shell_quote(first_tab['command'])} C-m"
        )
    for tab in tabs[1:]:
        window_name = tab["tabName"]
        cwd = normalize_cwd(tab["startDir"])
        commands.append(
            f"tmux new-window -t {shell_quote(session_target)} -n {shell_quote(window_name)} -c {shell_quote(cwd)}"
        )
        if tab["command"].strip():
            target = f"{session_name}:{window_name}"
            commands.append(
                f"tmux send-keys -t {shell_quote(target)} {shell_quote(tab['command'])} C-m"
            )
    commands.append(f"tmux select-window -t {shell_quote(first_target)}")
    return commands


def build_tmux_merge_commands(
    layout_config: LayoutConfig,
    session_name: str,
    on_conflict: TmuxMergeConflictAction,
) -> list[str]:
    validate_layout_config(layout_config)
    existing_window_names = list_tmux_window_names(session_name=session_name)
    first_target: str | None = None
    commands: list[str] = []

    for tab in layout_config["layoutTabs"]:
        window_name = tab["tabName"]
        cwd = normalize_cwd(tab["startDir"])
        command = tab["command"]
        target = f"{session_name}:{window_name}"
        window_exists = window_name in existing_window_names

        match on_conflict:
            case "mergeNewWindowsSkipMatchingWindows":
                if window_exists:
                    continue
                commands.extend(
                    _build_new_window_commands(
                        session_name=session_name,
                        window_name=window_name,
                        cwd=cwd,
                        command=command,
                    )
                )
            case "mergeNewWindowsOverwriteMatchingWindows":
                if window_exists:
                    commands.extend(
                        _build_replace_window_commands(
                            session_name=session_name,
                            window_name=window_name,
                            cwd=cwd,
                            command=command,
                            reserved_window_names=existing_window_names,
                        )
                    )
                else:
                    commands.extend(
                        _build_new_window_commands(
                            session_name=session_name,
                            window_name=window_name,
                            cwd=cwd,
                            command=command,
                        )
                    )
            case _:
                raise ValueError(f"Unsupported tmux merge policy: {on_conflict}")

        existing_window_names.add(window_name)
        if first_target is None:
            first_target = target

    if first_target is not None:
        commands.append(f"tmux select-window -t {shell_quote(first_target)}")
    return commands


def build_tmux_script(layout_config: LayoutConfig, session_name: str) -> str:
    script_lines = ["#!/usr/bin/env bash", "set -e"]
    script_lines.extend(build_tmux_commands(layout_config, session_name))
    return "\n".join(script_lines) + "\n"


def build_tmux_merge_script(
    layout_config: LayoutConfig,
    session_name: str,
    on_conflict: TmuxMergeConflictAction,
) -> str:
    script_lines = ["#!/usr/bin/env bash", "set -e"]
    script_lines.extend(
        build_tmux_merge_commands(
            layout_config=layout_config,
            session_name=session_name,
            on_conflict=on_conflict,
        )
    )
    return "\n".join(script_lines) + "\n"


def check_tmux_session_status(session_name: str) -> TmuxSessionStatus:
    try:
        result = subprocess.run(["tmux", "list-sessions", "-F", "#{session_name}"], capture_output=True, text=True, timeout=5)
    except FileNotFoundError as exc:
        return {
            "tmux_running": False,
            "session_exists": False,
            "session_name": session_name,
            "all_sessions": [],
            "error": str(exc),
        }
    except Exception as exc:
        return {
            "tmux_running": False,
            "session_exists": False,
            "session_name": session_name,
            "all_sessions": [],
            "error": str(exc),
        }

    if result.returncode != 0:
        stderr = (result.stderr or "").strip().lower()
        if "no server running" in stderr:
            return {"tmux_running": False, "session_exists": False, "session_name": session_name, "all_sessions": []}
        return {
            "tmux_running": False,
            "session_exists": False,
            "session_name": session_name,
            "all_sessions": [],
            "error": (result.stderr or result.stdout or "Unknown error").strip(),
        }

    sessions = [line.strip() for line in (result.stdout or "").splitlines() if line.strip()]
    return {
        "tmux_running": True,
        "session_exists": session_name in sessions,
        "session_name": session_name,
        "all_sessions": sessions,
    }


def build_unknown_command_status(tab_config: TabConfig) -> CommandStatus:
    return {
        "status": "unknown",
        "running": False,
        "processes": [],
        "command": tab_config["command"],
        "tab_name": tab_config["tabName"],
        "cwd": tab_config["startDir"],
    }
