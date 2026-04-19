

import subprocess

import pytest

from stackops.cluster.sessions_managers.windows_terminal.wt_utils.remote_executor import WTRemoteExecutor


def _completed_process(*, returncode: int, stdout: str, stderr: str) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=["ssh"], returncode=returncode, stdout=stdout, stderr=stderr)


def test_run_command_wraps_non_powershell_command_before_ssh(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_commands: list[list[str]] = []

    def fake_run(command: list[str], *, capture_output: bool, text: bool, timeout: int) -> subprocess.CompletedProcess[str]:
        assert capture_output is True
        assert text is True
        assert timeout == 7
        captured_commands.append(command)
        return _completed_process(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    executor = WTRemoteExecutor("node-a")
    result = executor.run_command("Get-ChildItem", timeout=7)

    assert result.stdout == "ok"
    assert captured_commands == [["ssh", "node-a", 'powershell -Command "Get-ChildItem"']]


def test_copy_file_to_remote_returns_failure_payload_on_scp_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(command: list[str], *, capture_output: bool, text: bool) -> subprocess.CompletedProcess[str]:
        assert capture_output is True
        assert text is True
        assert command == ["scp", "/tmp/demo.txt", "node-a:C:/temp/demo.txt"]
        return _completed_process(returncode=1, stdout="", stderr="permission denied")

    monkeypatch.setattr(subprocess, "run", fake_run)

    executor = WTRemoteExecutor("node-a")
    result = executor.copy_file_to_remote("/tmp/demo.txt", "C:/temp/demo.txt")

    assert result == {"success": False, "error": "permission denied"}


def test_create_remote_directory_returns_false_when_remote_command_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    executor = WTRemoteExecutor("node-a")

    def fake_run_command(command: str, timeout: int = 30) -> subprocess.CompletedProcess[str]:
        assert command == "New-Item -ItemType Directory -Path 'C:/logs' -Force"
        assert timeout == 30
        raise RuntimeError("ssh failed")

    monkeypatch.setattr(executor, "run_command", fake_run_command)

    assert executor.create_remote_directory("C:/logs") is False


def test_kill_wt_processes_formats_requested_process_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    executor = WTRemoteExecutor("node-a")
    captured_commands: list[tuple[str, int]] = []

    def fake_run_command(command: str, timeout: int = 30) -> subprocess.CompletedProcess[str]:
        captured_commands.append((command, timeout))
        return _completed_process(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(executor, "run_command", fake_run_command)

    result = executor.kill_wt_processes([101, 202])

    assert captured_commands == [("Stop-Process -Id 101,202 -Force", 10)]
    assert result == {"success": True, "message": "Processes killed", "remote": "node-a"}
