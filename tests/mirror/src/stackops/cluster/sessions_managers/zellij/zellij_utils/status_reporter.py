

from pathlib import Path

import pytest

from stackops.cluster.sessions_managers.zellij.zellij_utils import status_reporter as subject
from stackops.cluster.sessions_managers.zellij.zellij_utils.monitoring_types import CommandStatus
from stackops.cluster.sessions_managers.zellij.zellij_utils.process_monitor import ProcessMonitor
from stackops.cluster.sessions_managers.zellij.zellij_utils.remote_executor import RemoteExecutor
from stackops.cluster.sessions_managers.zellij.zellij_utils.session_manager import SessionManager
from stackops.utils.schemas.layouts.layout_types import LayoutConfig


def _make_layout_config() -> LayoutConfig:
    return {
        "layoutName": "Status",
        "layoutTabs": [
            {"tabName": "worker", "startDir": "/repo", "command": "python worker.py"},
            {"tabName": "logs", "startDir": "/repo", "command": "tail -f app.log"},
        ],
    }


class FakeProcessMonitor(ProcessMonitor):
    def __init__(self, remote_name: str, commands_status: dict[str, CommandStatus]) -> None:
        super().__init__(RemoteExecutor(remote_name))
        self.commands_status = commands_status
        self.layouts_seen: list[LayoutConfig] = []

    def check_all_commands_status(self, layout_config: LayoutConfig) -> dict[str, CommandStatus]:
        self.layouts_seen.append(layout_config)
        return self.commands_status


class FakeSessionManager(SessionManager):
    def __init__(self, remote_name: str, session_name: str, session_status: dict[str, object]) -> None:
        super().__init__(RemoteExecutor(remote_name), session_name, Path.home())
        self.session_status = session_status

    def check_zellij_session_status(self) -> dict[str, object]:
        return self.session_status


class EchoConsole:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def print(self, message: str) -> None:
        self.messages.append(message)
        print(message)



def test_get_comprehensive_status_summarizes_running_commands() -> None:
    process_monitor = FakeProcessMonitor(
        "srv-1",
        {
            "worker": {"status": "running", "running": True, "processes": [], "command": "python worker.py", "tab_name": "worker"},
            "logs": {"status": "not_running", "running": False, "processes": [], "command": "tail -f app.log", "tab_name": "logs"},
        },
    )
    session_manager = FakeSessionManager(
        "srv-1",
        "main-session",
        {"zellij_running": True, "session_exists": True, "session_name": "main-session", "all_sessions": ["main-session"]},
    )
    reporter = subject.StatusReporter(process_monitor, session_manager)

    status = reporter.get_comprehensive_status(_make_layout_config())

    assert process_monitor.layouts_seen == [_make_layout_config()]
    assert status["summary"] == {
        "total_commands": 2,
        "running_commands": 1,
        "stopped_commands": 1,
        "session_healthy": True,
        "remote": "srv-1",
    }



def test_print_status_report_emits_human_readable_summary(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    process_monitor = FakeProcessMonitor(
        "srv-2",
        {
            "worker": {
                "status": "running",
                "running": True,
                "processes": [{"pid": 11, "name": "python", "cmdline": ["python", "worker.py"], "status": "running"}],
                "command": "python worker.py",
                "tab_name": "worker",
            }
        },
    )
    session_manager = FakeSessionManager(
        "srv-2",
        "main-session",
        {"zellij_running": True, "session_exists": True, "session_name": "main-session", "all_sessions": ["main-session"]},
    )
    reporter = subject.StatusReporter(process_monitor, session_manager)
    fake_console = EchoConsole()
    monkeypatch.setattr(subject, "console", fake_console)

    reporter.print_status_report({"layoutName": "Status", "layoutTabs": [{"tabName": "worker", "startDir": "/repo", "command": "python worker.py"}]})

    output = capsys.readouterr().out
    assert "ZELLIJ REMOTE LAYOUT STATUS REPORT (srv-2)" in output
    assert "Zellij session 'main-session' is running on srv-2" in output
    assert "worker: Running on srv-2" in output
    assert "PID 11: python (running)" in output
    assert "Session healthy: ✅" in output
    assert fake_console.messages == ["   [dim]└─[/dim] PID 11: python (running)"]
