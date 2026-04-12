from __future__ import annotations

from pathlib import Path
import subprocess

from machineconfig.cluster.sessions_managers.zellij.zellij_utils import session_manager as subject
from machineconfig.cluster.sessions_managers.zellij.zellij_utils.remote_executor import RemoteExecutor


type RunResponse = subprocess.CompletedProcess[str] | Exception


class FakeRemoteExecutor(RemoteExecutor):
    def __init__(self, remote_name: str, run_responses: list[RunResponse]) -> None:
        super().__init__(remote_name)
        self.run_responses: list[RunResponse] = run_responses
        self.run_calls: list[tuple[str, int]] = []
        self.directory_calls: list[str] = []
        self.copy_calls: list[tuple[str, str]] = []
        self.copy_file_result: dict[str, bool | str] = {"success": True, "remote_path": ""}
        self.create_remote_directory_result = True
        self.attached_sessions: list[str] = []

    def run_command(self, command: str, timeout: int) -> subprocess.CompletedProcess[str]:
        self.run_calls.append((command, timeout))
        response = self.run_responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def create_remote_directory(self, remote_dir: str) -> bool:
        self.directory_calls.append(remote_dir)
        return self.create_remote_directory_result

    def copy_file_to_remote(self, local_file: str, remote_path: str) -> dict[str, bool | str]:
        self.copy_calls.append((local_file, remote_path))
        return self.copy_file_result

    def attach_to_session_interactive(self, session_name: str) -> None:
        self.attached_sessions.append(session_name)



def test_copy_layout_to_remote_uses_home_relative_remote_path(tmp_path: Path) -> None:
    local_layout_file = tmp_path.joinpath("layout.kdl")
    local_layout_file.write_text("layout {}\n", encoding="utf-8")
    remote_executor = FakeRemoteExecutor("srv-1", [])
    manager = subject.SessionManager(remote_executor, "main-session", Path.home().joinpath("tmp_results", "zellij_layouts"))

    remote_path = manager.copy_layout_to_remote(local_layout_file, random_suffix="abc123")

    assert remote_executor.directory_calls == ["~/tmp_results/zellij_layouts"]
    assert remote_executor.copy_calls == [(str(local_layout_file), "~/tmp_results/zellij_layouts/zellij_layout_main-session_abc123.kdl")]
    assert remote_path == "~/tmp_results/zellij_layouts/zellij_layout_main-session_abc123.kdl"



def test_check_zellij_session_status_parses_remote_sessions() -> None:
    remote_executor = FakeRemoteExecutor(
        "srv-2",
        [subprocess.CompletedProcess(args=["ssh"], returncode=0, stdout="other\nmain-session [Created]\n", stderr="")],
    )
    manager = subject.SessionManager(remote_executor, "main-session", Path.home().joinpath("tmp_results", "zellij_layouts"))

    status = manager.check_zellij_session_status()

    assert status["zellij_running"] is True
    assert status["session_exists"] is True
    assert status["all_sessions"] == ["other", "main-session [Created]"]
    assert status["remote"] == "srv-2"



def test_start_zellij_session_uses_layout_basename_on_remote() -> None:
    remote_executor = FakeRemoteExecutor(
        "srv-3",
        [subprocess.CompletedProcess(args=["ssh"], returncode=0, stdout="started\n", stderr="")],
    )
    manager = subject.SessionManager(remote_executor, "main-session", Path.home().joinpath("tmp_results", "zellij_layouts"))

    result = manager.start_zellij_session("/tmp/custom/layout.kdl")

    assert result["success"] is True
    assert remote_executor.run_calls == [("zellij --layout ~/tmp_results/zellij_layouts/layout.kdl a -b main-session", 30)]



def test_start_zellij_session_without_layout_path_returns_error() -> None:
    manager = subject.SessionManager(FakeRemoteExecutor("srv-4", []), "main-session", Path.home().joinpath("tmp_results", "zellij_layouts"))

    result = manager.start_zellij_session(None)

    assert result["success"] is False
    assert "No layout file path provided." in result["error"]



def test_attach_to_session_delegates_to_remote_executor() -> None:
    remote_executor = FakeRemoteExecutor("srv-5", [])
    manager = subject.SessionManager(remote_executor, "main-session", Path.home().joinpath("tmp_results", "zellij_layouts"))

    manager.attach_to_session()

    assert remote_executor.attached_sessions == ["main-session"]
