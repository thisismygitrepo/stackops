#!/usr/bin/env python3
import subprocess
from typing import NotRequired, TypedDict

from stackops.cluster.sessions_managers.monitoring_types import CommandStatus
from stackops.utils.schemas.layouts.layout_types import LayoutConfig


class TmuxSessionStatus(TypedDict):
    tmux_running: bool
    session_exists: bool
    session_name: str
    all_sessions: list[str]
    error: NotRequired[str]


def check_tmux_session_status(session_name: str) -> TmuxSessionStatus:
    try:
        result = subprocess.run(
            ["tmux", "list-sessions", "-F", "#{session_name}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
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
            return {
                "tmux_running": False,
                "session_exists": False,
                "session_name": session_name,
                "all_sessions": [],
            }
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


def build_unknown_commands_status(layout_config: LayoutConfig) -> dict[str, CommandStatus]:
    commands_status: dict[str, CommandStatus] = {}
    for tab in layout_config["layoutTabs"]:
        for pane in tab["panes"]:
            commands_status[f"{tab['tabName']}/{pane['paneName']}"] = {
                "status": "unknown",
                "running": False,
                "processes": [],
                "command": pane["command"],
                "tab_name": tab["tabName"],
                "pane_name": pane["paneName"],
                "cwd": pane["startDir"],
            }
    return commands_status
