from __future__ import annotations

import pytest

import machineconfig.cluster.sessions_managers.windows_terminal.wt_utils.status_reporting as status_reporting


class _FakeConsole:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def print(self, message: str) -> None:
        self.messages.append(message)


def test_calculate_session_summary_counts_running_and_stopped_commands() -> None:
    commands_status = {"api": {"running": True}, "worker": {"running": False}, "watcher": {"running": True}}

    summary = status_reporting.calculate_session_summary(commands_status, session_healthy=False)

    assert summary == {"total_commands": 3, "running_commands": 2, "stopped_commands": 1, "session_healthy": False}


def test_calculate_global_summary_from_status_collects_unique_remote_names() -> None:
    all_status = {
        "session-a": {"summary": {"session_healthy": True, "total_commands": 2, "running_commands": 1}, "remote_name": "node-a"},
        "session-b": {"summary": {"session_healthy": False, "total_commands": 3, "running_commands": 2}, "remote_name": "node-a"},
        "session-c": {"summary": {"session_healthy": True, "total_commands": 1, "running_commands": 1}, "remote_name": "node-c"},
    }

    summary = status_reporting.calculate_global_summary_from_status(all_status, include_remote_machines=True)

    assert summary["total_sessions"] == 3
    assert summary["healthy_sessions"] == 2
    assert summary["stopped_commands"] == 2
    assert summary["all_sessions_healthy"] is False
    assert set(summary["remote_machines"]) == {"node-a", "node-c"}


def test_print_commands_status_truncates_long_commands_and_limits_process_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_console = _FakeConsole()
    monkeypatch.setattr(status_reporting, "console", fake_console)

    commands_status = {
        "api": {
            "running": True,
            "command": "x" * 55,
            "processes": [{"pid": 1, "name": "python"}, {"pid": 2, "name": "watcher"}, {"pid": 3, "name": "ignored"}],
        }
    }

    status_reporting.print_commands_status(commands_status, summary={"running_commands": 1, "total_commands": 1})

    assert fake_console.messages == [f"     ✅ api: {'x' * 50}...", "        [dim]└─[/dim] PID 1: python", "        [dim]└─[/dim] PID 2: watcher"]
