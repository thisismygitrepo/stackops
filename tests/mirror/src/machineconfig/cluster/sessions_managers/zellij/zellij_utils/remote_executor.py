from __future__ import annotations

import subprocess

import pytest

from machineconfig.cluster.sessions_managers.zellij.zellij_utils import remote_executor as subject


def test_run_command_uses_ssh_with_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[list[str], bool, bool, int | None]] = []

    def fake_run(args: list[str], capture_output: bool = False, text: bool = False, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
        calls.append((args, capture_output, text, timeout))
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="alex\n", stderr="")

    monkeypatch.setattr(subject.subprocess, "run", fake_run)
    executor = subject.RemoteExecutor("srv-1")

    result = executor.run_command("whoami", timeout=7)

    assert result.stdout == "alex\n"
    assert calls == [(["ssh", "srv-1", "whoami"], True, True, 7)]


def test_copy_file_to_remote_returns_error_details_on_scp_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(args: list[str], capture_output: bool = False, text: bool = False) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="permission denied")

    monkeypatch.setattr(subject.subprocess, "run", fake_run)
    executor = subject.RemoteExecutor("srv-2")

    result = executor.copy_file_to_remote("local.kdl", "~/remote.kdl")

    assert result == {"success": False, "error": "permission denied"}


def test_create_remote_directory_returns_true_when_remote_command_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[tuple[str, int]] = []

    def fake_run_command(command: str, timeout: int) -> subprocess.CompletedProcess[str]:
        commands.append((command, timeout))
        return subprocess.CompletedProcess(args=["ssh"], returncode=0, stdout="", stderr="")

    executor = subject.RemoteExecutor("srv-3")
    monkeypatch.setattr(executor, "run_command", fake_run_command)

    assert executor.create_remote_directory("~/tmp/layouts") is True
    assert commands == [("mkdir -p ~/tmp/layouts", 30)]


def test_attach_to_session_interactive_uses_tty_ssh(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(args: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subject.subprocess, "run", fake_run)
    executor = subject.RemoteExecutor("srv-4")

    executor.attach_to_session_interactive("main-session")

    assert calls == [["ssh", "-t", "srv-4", "zellij attach main-session"]]
