

import json
import subprocess
from pathlib import Path
from typing import NotRequired, TypedDict, cast

import pytest

import stackops.cluster.sessions_managers.windows_terminal.wt_utils.session_manager as session_manager_module
from stackops.cluster.sessions_managers.windows_terminal.wt_utils.remote_executor import WTRemoteExecutor
from stackops.cluster.sessions_managers.windows_terminal.wt_utils.session_manager import WTSessionManager


class _CopyResult(TypedDict):
    success: bool
    remote_path: NotRequired[str]
    error: NotRequired[str]


def _completed_process(*, returncode: int, stdout: str, stderr: str) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=["powershell"], returncode=returncode, stdout=stdout, stderr=stderr)


class _FakeRemoteExecutor:
    def __init__(self, remote_name: str, copy_result: _CopyResult) -> None:
        self.remote_name = remote_name
        self.copy_result = copy_result
        self.created_directories: list[str] = []
        self.copied_files: list[tuple[str, str]] = []

    def create_remote_directory(self, remote_dir: str) -> bool:
        self.created_directories.append(remote_dir)
        return True

    def copy_file_to_remote(self, local_file: str, remote_path: str) -> _CopyResult:
        self.copied_files.append((local_file, remote_path))
        return self.copy_result

    def run_command(self, command: str, timeout: int = 30) -> subprocess.CompletedProcess[str]:
        return _completed_process(returncode=0, stdout=command, stderr="")


def test_copy_script_to_remote_returns_local_path_for_local_manager() -> None:
    local_script = Path("/tmp/layout.ps1")
    manager = WTSessionManager(remote_executor=None, session_name="alpha", tmp_layout_dir=Path("/tmp/layouts"))

    assert manager.copy_script_to_remote(local_script, "xyz") == str(local_script)


def test_copy_script_to_remote_creates_home_relative_remote_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_home() -> Path:
        return tmp_path

    monkeypatch.setattr(session_manager_module.Path, "home", staticmethod(fake_home))

    local_script = tmp_path / "layout.ps1"
    local_script.write_text("Write-Output 'hi'", encoding="utf-8")
    remote_executor = _FakeRemoteExecutor(remote_name="node-a", copy_result={"success": True, "remote_path": "~/layouts/wt_script_alpha_xyz.ps1"})
    manager = WTSessionManager(remote_executor=cast(WTRemoteExecutor, remote_executor), session_name="alpha", tmp_layout_dir=tmp_path / "layouts")

    remote_path = manager.copy_script_to_remote(local_script, "xyz")

    assert remote_executor.created_directories == ["~/layouts"]
    assert remote_executor.copied_files == [(str(local_script), "~/layouts/wt_script_alpha_xyz.ps1")]
    assert remote_path == "~/layouts/wt_script_alpha_xyz.ps1"


def test_start_wt_session_uses_home_relative_script_path_for_remote_manager(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_home() -> Path:
        return tmp_path

    monkeypatch.setattr(session_manager_module.Path, "home", staticmethod(fake_home))

    remote_executor = _FakeRemoteExecutor(remote_name="node-a", copy_result={"success": True, "remote_path": "~/layouts/demo.ps1"})
    manager = WTSessionManager(remote_executor=cast(WTRemoteExecutor, remote_executor), session_name="alpha", tmp_layout_dir=tmp_path / "layouts")
    captured_commands: list[tuple[str, int]] = []

    def fake_run_command(command: str, timeout: int = 30) -> subprocess.CompletedProcess[str]:
        captured_commands.append((command, timeout))
        return _completed_process(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(manager, "_run_command", fake_run_command)

    result = manager.start_wt_session(script_file_path="/tmp/random/demo.ps1")

    assert captured_commands == [("powershell -ExecutionPolicy Bypass -File '~/layouts/demo.ps1'", 30)]
    assert result == {"success": True, "session_name": "alpha", "location": "node-a", "message": "Session started successfully"}


def test_check_wt_session_status_parses_json_and_matches_empty_titles(monkeypatch: pytest.MonkeyPatch) -> None:
    manager = WTSessionManager(remote_executor=None, session_name="alpha", tmp_layout_dir=Path("/tmp/layouts"))
    payload = json.dumps(
        [
            {"Id": 10, "ProcessName": "WindowsTerminal", "StartTime": "now", "MainWindowTitle": "alpha main"},
            {"Id": 11, "ProcessName": "WindowsTerminal", "StartTime": "now", "MainWindowTitle": ""},
        ]
    )

    def fake_run_command(command: str, timeout: int = 30) -> subprocess.CompletedProcess[str]:
        assert "Get-Process -Name 'WindowsTerminal'" in command
        assert timeout == 10
        return _completed_process(returncode=0, stdout=payload, stderr="")

    monkeypatch.setattr(manager, "_run_command", fake_run_command)

    status = manager.check_wt_session_status()

    assert status["wt_running"] is True
    assert status["session_exists"] is True
    assert status["session_name"] == "alpha"
    assert status["location"] == "local"
    assert len(status["all_windows"]) == 2
    assert len(status["session_windows"]) == 2
