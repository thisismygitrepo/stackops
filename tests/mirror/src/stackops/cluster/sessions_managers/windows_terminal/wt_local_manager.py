

import json
import subprocess
from pathlib import Path
from typing import ClassVar

import pytest

from stackops.cluster.sessions_managers.session_exit_mode import SessionExitMode
from stackops.cluster.sessions_managers.windows_terminal import wt_local_manager as local_manager_module
from stackops.utils.schemas.layouts.layout_types import LayoutConfig


def _make_layout(layout_name: str, command: str) -> LayoutConfig:
    return {"layoutName": layout_name, "layoutTabs": [{"tabName": f"{layout_name}-tab", "startDir": "~/repo", "command": command}]}


def _completed_process(returncode: int, stdout: str, stderr: str) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=["powershell"], returncode=returncode, stdout=stdout, stderr=stderr)


class FakeWTLayoutGenerator:
    created_sessions: ClassVar[list[str]] = []

    def __init__(self, layout_config: LayoutConfig, session_name: str, exit_mode: SessionExitMode) -> None:
        self.layout_config: LayoutConfig = layout_config
        self.session_name: str = session_name
        self.exit_mode: SessionExitMode = exit_mode
        self.script_path: str | None = None

    def create_layout_file(self) -> None:
        self.script_path = f"/tmp/{self.session_name}.ps1"
        self.__class__.created_sessions.append(self.session_name)

    def check_all_commands_status(self) -> dict[str, dict[str, object]]:
        return {tab["tabName"]: {"running": True, "command": tab["command"], "processes": []} for tab in self.layout_config["layoutTabs"]}


def test_save_and_load_round_trip(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(local_manager_module, "WTLayoutGenerator", FakeWTLayoutGenerator)
    monkeypatch.setattr(local_manager_module, "TMP_SERIALIZATION_DIR", tmp_path)

    layouts: list[LayoutConfig] = [_make_layout("alpha", "python alpha.py"), _make_layout("beta", "python beta.py")]
    manager = local_manager_module.WTLocalManager(session_layouts=layouts, session_name_prefix="pref", exit_mode="terminate")

    session_id = manager.save("sess0001")
    loaded = local_manager_module.WTLocalManager.load(session_id)

    assert (tmp_path / session_id / "session_layouts.json").is_file()
    assert loaded.session_name_prefix == "pref"
    assert loaded.exit_mode == "terminate"
    assert [manager_item.session_name for manager_item in loaded.managers] == ["alpha", "beta"]
    assert [manager_item.script_path for manager_item in loaded.managers] == ["/tmp/alpha.ps1", "/tmp/beta.ps1"]


def test_start_all_sessions_handles_success_missing_script_and_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(local_manager_module, "WTLayoutGenerator", FakeWTLayoutGenerator)

    layouts: list[LayoutConfig] = [
        _make_layout("alpha", "python alpha.py"),
        _make_layout("beta", "python beta.py"),
        _make_layout("gamma", "python gamma.py"),
    ]
    manager = local_manager_module.WTLocalManager(session_layouts=layouts, session_name_prefix="pref", exit_mode="backToShell")
    manager.managers[1].script_path = None

    def fake_run(cmd: str, shell: bool, capture_output: bool, text: bool, timeout: int, check: bool) -> subprocess.CompletedProcess[str]:
        assert shell is True
        assert capture_output is True
        assert text is True
        assert check is False
        assert timeout == 30
        if "alpha.ps1" in cmd:
            return _completed_process(returncode=0, stdout="", stderr="")
        raise RuntimeError("pow")

    monkeypatch.setattr(local_manager_module.subprocess, "run", fake_run)

    result = manager.start_all_sessions()

    assert result["alpha"]["success"] is True
    assert result["beta"] == {"success": False, "error": "No script file path available"}
    assert result["gamma"] == {"success": False, "error": "pow"}


def test_attach_to_session_lists_all_commands_and_rejects_unknown_session(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(local_manager_module, "WTLayoutGenerator", FakeWTLayoutGenerator)

    manager = local_manager_module.WTLocalManager(
        session_layouts=[_make_layout("alpha", "python alpha.py"), _make_layout("beta", "python beta.py")],
        session_name_prefix="pref",
        exit_mode="killWindow",
    )

    attachment_commands = manager.attach_to_session()

    assert "wt -w alpha" in attachment_commands
    assert "wt -w beta" in attachment_commands
    with pytest.raises(ValueError, match="Session 'missing' not found"):
        manager.attach_to_session("missing")


def test_list_active_sessions_reads_json_process_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(local_manager_module, "WTLayoutGenerator", FakeWTLayoutGenerator)

    manager = local_manager_module.WTLocalManager(
        session_layouts=[_make_layout("alpha", "python alpha.py"), _make_layout("beta", "python beta.py")],
        session_name_prefix="pref",
        exit_mode="backToShell",
    )
    payload = json.dumps([{"MainWindowTitle": "alpha"}, {"MainWindowTitle": "unrelated"}])

    def fake_run(args: list[str], capture_output: bool, text: bool, timeout: int, check: bool) -> subprocess.CompletedProcess[str]:
        assert args[0] == "powershell"
        assert capture_output is True
        assert text is True
        assert timeout == 10
        assert check is False
        return _completed_process(returncode=0, stdout=payload, stderr="")

    monkeypatch.setattr(local_manager_module.subprocess, "run", fake_run)

    active_sessions = manager.list_active_sessions()

    assert active_sessions == [
        {"session_name": "alpha", "is_active": True, "tab_count": 1, "tabs": ["alpha-tab"]},
        {"session_name": "beta", "is_active": False, "tab_count": 1, "tabs": ["beta-tab"]},
    ]
