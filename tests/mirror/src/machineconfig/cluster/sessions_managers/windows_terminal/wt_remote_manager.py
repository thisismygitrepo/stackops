from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from machineconfig.cluster.sessions_managers.windows_terminal import wt_remote_manager as remote_manager_module


class FakeRemoteExecutor:
    def __init__(self, remote_name: str) -> None:
        self.remote_name: str = remote_name
        self.raise_windows_info_error: str | None = None
        self.last_command: str | None = None

    def get_remote_windows_info(self) -> dict[str, object]:
        if self.raise_windows_info_error is not None:
            raise RuntimeError(self.raise_windows_info_error)
        return {"wt_available": True, "windows_info": f"Windows on {self.remote_name}"}

    def list_wt_processes(self) -> dict[str, object]:
        return {"success": True, "processes": "wt.exe"}

    def run_command(self, command: str) -> None:
        self.last_command = command


class FakeRemoteSessionManager:
    def __init__(self, session_name: str) -> None:
        self.session_name: str = session_name
        self.start_result: dict[str, object] = {"success": True}
        self.start_error: str | None = None
        self.wt_status: dict[str, object] = {"wt_running": True}
        self.wt_version: dict[str, object] = {"success": True, "version": "1.0.0"}

    def start_wt_session(self, script_path: str | None) -> dict[str, object]:
        if self.start_error is not None:
            raise RuntimeError(self.start_error)
        return {**self.start_result, "script_path": script_path}

    def check_wt_session_status(self) -> dict[str, object]:
        return self.wt_status

    def get_wt_version(self) -> dict[str, object]:
        return self.wt_version


class FakeProcessMonitor:
    def __init__(self) -> None:
        self.raise_error: str | None = None

    def check_all_commands_status(self, tabs: list[dict[str, object]]) -> dict[str, dict[str, object]]:
        if self.raise_error is not None:
            raise RuntimeError(self.raise_error)
        return {str(tab["tabName"]): {"running": True, "command": tab["command"], "processes": [1]} for tab in tabs}


class FakeWTRemoteLayoutGenerator:
    def __init__(self, layout_config: dict[str, object], remote_name: str, session_name: str) -> None:
        self.layout_config: dict[str, object] = layout_config
        self.remote_name: str = remote_name
        self.session_name: str = session_name
        self.script_path: str | None = f"/tmp/{remote_name}-{session_name}.ps1"
        self.remote_executor = FakeRemoteExecutor(remote_name)
        self.session_manager = FakeRemoteSessionManager(session_name)
        self.process_monitor = FakeProcessMonitor()

    def create_layout_file(self) -> None:
        return None

    def to_json(self, file_path: str) -> str:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "layout_config": self.layout_config,
                    "remote_name": self.remote_name,
                    "session_name": self.session_name,
                    "script_path": self.script_path,
                }
            ),
            encoding="utf-8",
        )
        return str(path)

    @classmethod
    def from_json(cls, file_path: str) -> "FakeWTRemoteLayoutGenerator":
        data = json.loads(Path(file_path).read_text(encoding="utf-8"))
        instance = cls(layout_config=data["layout_config"], remote_name=data["remote_name"], session_name=data["session_name"])
        instance.script_path = data["script_path"]
        return instance


def test_init_builds_remote_generators_and_ssh_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(remote_manager_module, "WTRemoteLayoutGenerator", FakeWTRemoteLayoutGenerator)
    monkeypatch.setattr(remote_manager_module, "generate_random_suffix", lambda length: "fixed123")
    monkeypatch.setattr(remote_manager_module, "run_command_in_wt_tab", lambda command, tab_name, cwd: f"RUN {tab_name}: {command} @ {cwd}")

    manager = remote_manager_module.WTSessionManager(
        machine2wt_tabs={"srv-a": {"api": ("~/repo", "python api.py")}, "srv-b": {"jobs": ("~/jobs", "python jobs.py")}}, session_name_prefix="Jobs"
    )

    assert [item.session_name for item in manager.managers] == ["Jobs_fixed123", "Jobs_fixed123"]
    assert manager.managers[0].layout_config["layoutName"] == "Jobs_srv-a"
    assert manager.managers[0].layout_config["layoutTabs"] == [{"tabName": "api", "startDir": "~/repo", "command": "python api.py", "tabWeight": 1}]
    ssh_commands = manager.ssh_to_all_machines()
    assert "RUN srv-a: ssh srv-a -t 'wt -w Jobs_fixed123' @ None" in ssh_commands
    assert "RUN srv-b: ssh srv-b -t 'wt -w Jobs_fixed123' @ None" in ssh_commands


def test_save_and_load_round_trip_uses_manager_json_files(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(remote_manager_module, "WTRemoteLayoutGenerator", FakeWTRemoteLayoutGenerator)
    monkeypatch.setattr(remote_manager_module, "generate_random_suffix", lambda length: "fixed123")
    monkeypatch.setattr(remote_manager_module, "TMP_SERIALIZATION_DIR", tmp_path)

    manager = remote_manager_module.WTSessionManager(machine2wt_tabs={"srv-a": {"api": ("~/repo", "python api.py")}}, session_name_prefix="Jobs")

    session_id = manager.save("sess-0001")
    loaded = remote_manager_module.WTSessionManager.load(session_id)

    assert (tmp_path / session_id / "machine2wt_tabs.json").is_file()
    assert [item.remote_name for item in loaded.managers] == ["srv-a"]
    assert [item.session_name for item in loaded.managers] == ["Jobs_fixed123"]
    assert remote_manager_module.WTSessionManager.list_saved_sessions() == ["sess-0001"]
    assert remote_manager_module.WTSessionManager.delete_session("sess-0001") is True


def test_start_status_and_remote_overview_handle_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(remote_manager_module, "WTRemoteLayoutGenerator", FakeWTRemoteLayoutGenerator)
    monkeypatch.setattr(remote_manager_module, "generate_random_suffix", lambda length: "fixed123")

    manager = remote_manager_module.WTSessionManager(
        machine2wt_tabs={"srv-a": {"api": ("~/repo", "python api.py")}, "srv-b": {"jobs": ("~/jobs", "python jobs.py")}}, session_name_prefix="Jobs"
    )

    broken_manager = cast(FakeWTRemoteLayoutGenerator, manager.managers[1])
    broken_manager.session_manager.start_error = "cannot start"
    broken_manager.process_monitor.raise_error = "process boom"
    broken_manager.remote_executor.raise_windows_info_error = "remote boom"

    start_results = manager.start_all_sessions()
    status = manager.check_all_sessions_status()
    overview = manager.get_remote_overview()

    assert start_results["srv-a:Jobs_fixed123"]["success"] is True
    assert start_results["srv-b:Jobs_fixed123"]["error"] == "cannot start"
    assert status["srv-a:Jobs_fixed123"]["summary"]["session_healthy"] is True
    assert status["srv-b:Jobs_fixed123"]["error"] == "process boom"
    assert overview["srv-a"]["wt_version"]["version"] == "1.0.0"
    assert overview["srv-b"]["error"] == "remote boom"
