from __future__ import annotations

from dataclasses import dataclass, field
import subprocess

import pytest

from machineconfig.cluster.sessions_managers.zellij.zellij_utils import process_monitor as subject
from machineconfig.cluster.sessions_managers.zellij.zellij_utils.remote_executor import RemoteExecutor
from machineconfig.utils.schemas.layouts.layout_types import LayoutConfig


type RunResponse = subprocess.CompletedProcess[str] | Exception


def _make_layout_config() -> LayoutConfig:
    return {
        "layoutName": "Monitor",
        "layoutTabs": [
            {"tabName": "worker", "startDir": "/repo", "command": "python worker.py --port 9000"},
            {"tabName": "logs", "startDir": "/repo", "command": "tail -f app.log"},
        ],
    }


@dataclass(slots=True)
class FakeRemoteExecutor(RemoteExecutor):
    responses: list[RunResponse] = field(default_factory=list)
    calls: list[tuple[str, int]] = field(default_factory=list)

    def __init__(self, remote_name: str, responses: list[RunResponse]) -> None:
        super().__init__(remote_name)
        self.responses = responses
        self.calls = []

    def run_command(self, command: str, timeout: int) -> subprocess.CompletedProcess[str]:
        self.calls.append((command, timeout))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def test_check_command_status_returns_unknown_for_missing_tab() -> None:
    monitor = subject.ProcessMonitor(FakeRemoteExecutor("srv-1", []))

    result = monitor.check_command_status("missing", _make_layout_config(), use_verification=True)

    assert result["status"] == "unknown"
    assert result["running"] is False
    assert result["remote"] == "srv-1"
    assert "not found" in result["error"]


def test_basic_process_check_reports_running_processes() -> None:
    remote_executor = FakeRemoteExecutor(
        "srv-1",
        [
            subprocess.CompletedProcess(
                args=["ssh"],
                returncode=0,
                stdout='[{"pid": 42, "name": "python", "cmdline": ["python", "worker.py"], "status": "running"}]',
                stderr="",
            )
        ],
    )
    monitor = subject.ProcessMonitor(remote_executor)

    result = monitor._basic_process_check("worker", _make_layout_config())

    assert result["status"] == "running"
    assert result["running"] is True
    assert result["remote"] == "srv-1"
    assert result["processes"][0]["pid"] == 42
    assert remote_executor.calls[0][1] == 15


def test_force_fresh_process_check_records_timestamp_and_method() -> None:
    remote_executor = FakeRemoteExecutor(
        "srv-2",
        [
            subprocess.CompletedProcess(args=["ssh"], returncode=0, stdout="1700000000\n", stderr=""),
            subprocess.CompletedProcess(
                args=["ssh"],
                returncode=0,
                stdout='{"processes": [{"pid": 7, "name": "python", "cmdline": ["python", "worker.py"], "status": "running"}], "check_timestamp": 1700000000.5}',
                stderr="",
            ),
        ],
    )
    monitor = subject.ProcessMonitor(remote_executor)

    result = monitor.force_fresh_process_check("worker", _make_layout_config())

    assert remote_executor.calls[0] == ("date +%s", 5)
    assert remote_executor.calls[1][1] == 15
    assert result["status"] == "running"
    assert result["check_timestamp"] == "1700000000"
    assert result["method"] == "force_fresh_check"
    assert result["processes"][0]["pid"] == 7


def test_get_verified_process_status_filters_dead_processes(monkeypatch: pytest.MonkeyPatch) -> None:
    monitor = subject.ProcessMonitor(FakeRemoteExecutor("srv-3", []))

    def fake_force_fresh_process_check(tab_name: str, layout_config: LayoutConfig) -> subject.CommandStatus:
        return {
            "status": "running",
            "running": True,
            "processes": [
                {"pid": 11, "name": "python", "cmdline": ["python", "worker.py"], "status": "running"},
                {"pid": 12, "name": "python", "cmdline": ["python", "worker.py"], "status": "running"},
            ],
            "command": "python worker.py",
            "tab_name": tab_name,
        }

    def fake_verify_process_alive(pid: int) -> bool:
        return pid == 11

    monkeypatch.setattr(monitor, "force_fresh_process_check", fake_force_fresh_process_check)
    monkeypatch.setattr(monitor, "verify_process_alive", fake_verify_process_alive)

    result = monitor.get_verified_process_status("worker", _make_layout_config())

    assert result["status"] == "running"
    assert result["running"] is True
    assert result["verification_method"] == "kill_signal_check"
    assert [process["pid"] for process in result["processes"]] == [11]
    assert result["processes"][0]["verified_alive"] is True


def test_check_all_commands_status_uses_verified_checks(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, bool]] = []

    def fake_check_command_status(
        self: subject.ProcessMonitor, tab_name: str, layout_config: LayoutConfig, use_verification: bool
    ) -> subject.CommandStatus:
        calls.append((tab_name, use_verification))
        return {"status": "running", "running": True, "processes": [], "command": tab_name, "tab_name": tab_name}

    monkeypatch.setattr(subject.ProcessMonitor, "check_command_status", fake_check_command_status)
    monitor = subject.ProcessMonitor(FakeRemoteExecutor("srv-4", []))

    result = monitor.check_all_commands_status(_make_layout_config())

    assert calls == [("worker", True), ("logs", True)]
    assert set(result) == {"worker", "logs"}
