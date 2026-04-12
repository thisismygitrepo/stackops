from __future__ import annotations

import subprocess
from typing import cast

import pytest

from machineconfig.cluster.sessions_managers.windows_terminal.wt_utils import process_monitor as process_module
from machineconfig.utils.schemas.layouts.layout_types import TabConfig


def _completed_process(
    returncode: int,
    stdout: str,
    stderr: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=["powershell"], returncode=returncode, stdout=stdout, stderr=stderr)


def _make_tabs() -> list[TabConfig]:
    return [
        {
            "tabName": "api",
            "startDir": "~/repo",
            "command": "python api.py --port 8000",
        }
    ]


class FakeRemoteExecutor:
    def __init__(self, remote_name: str) -> None:
        self.remote_name: str = remote_name
        self.result = _completed_process(returncode=0, stdout="", stderr="")
        self.commands: list[tuple[str, int]] = []

    def run_command(
        self,
        command: str,
        timeout: int,
    ) -> subprocess.CompletedProcess[str]:
        self.commands.append((command, timeout))
        return self.result


def test_location_name_and_missing_tab_status() -> None:
    monitor = process_module.WTProcessMonitor(FakeRemoteExecutor("server-a"))

    status = monitor.check_command_status("missing", _make_tabs())

    assert monitor.location_name == "server-a"
    assert status["status"] == "unknown"
    assert status["running"] is False


def test_basic_process_check_parses_json_lines(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monitor = process_module.WTProcessMonitor()

    def fake_run_command(
        command: str,
        timeout: int,
    ) -> subprocess.CompletedProcess[str]:
        assert "Get-Process" in command
        assert timeout == 15
        return _completed_process(
            returncode=0,
            stdout='noise\n{"pid": 10, "name": "python"}\n{"pid": 11, "name": "pytest"}\n',
            stderr="",
        )

    monkeypatch.setattr(monitor, "_run_command", fake_run_command)

    status = monitor._basic_process_check("api", _make_tabs())
    processes = cast(list[dict[str, object]], status["processes"])

    assert status["status"] == "running"
    assert status["running"] is True
    assert [item["pid"] for item in processes] == [10, 11]


def test_force_fresh_process_check_and_verification_filter_dead_processes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monitor = process_module.WTProcessMonitor()

    def fake_run_command(
        command: str,
        timeout: int,
    ) -> subprocess.CompletedProcess[str]:
        if command == "Get-Date -UFormat %s":
            assert timeout == 5
            return _completed_process(returncode=0, stdout="1712345678\n", stderr="")
        assert timeout == 15
        return _completed_process(
            returncode=0,
            stdout='prefix\n{"processes": [{"pid": 10}, {"pid": 11}]}\n',
            stderr="",
        )

    def fake_verify_process_alive(pid: int) -> bool:
        return pid == 10

    monkeypatch.setattr(monitor, "_run_command", fake_run_command)
    monkeypatch.setattr(monitor, "verify_process_alive", fake_verify_process_alive)

    status = monitor.get_verified_process_status("api", _make_tabs())
    processes = cast(list[dict[str, object]], status["processes"])

    assert status["check_timestamp"] == "1712345678"
    assert status["running"] is True
    assert status["verification_method"] == "get_process_check"
    assert [item["pid"] for item in processes] == [10]
    assert processes[0]["verified_alive"] is True


def test_get_windows_terminal_windows_handles_valid_and_invalid_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monitor = process_module.WTProcessMonitor()

    def good_run_command(
        command: str,
        timeout: int,
    ) -> subprocess.CompletedProcess[str]:
        assert "WindowsTerminal" in command
        assert timeout == 15
        return _completed_process(
            returncode=0,
            stdout='{"Id": 1, "ProcessName": "WindowsTerminal"}',
            stderr="",
        )

    def bad_run_command(
        command: str,
        timeout: int,
    ) -> subprocess.CompletedProcess[str]:
        assert "WindowsTerminal" in command
        assert timeout == 15
        return _completed_process(returncode=0, stdout="{bad json}", stderr="")

    monkeypatch.setattr(monitor, "_run_command", good_run_command)
    good_status = monitor.get_windows_terminal_windows()
    monkeypatch.setattr(monitor, "_run_command", bad_run_command)
    bad_status = monitor.get_windows_terminal_windows()

    assert good_status["success"] is True
    assert cast(list[dict[str, object]], good_status["windows"])[0]["ProcessName"] == "WindowsTerminal"
    assert bad_status["success"] is False
    assert bad_status["error"] == "Failed to parse Windows Terminal process info"
