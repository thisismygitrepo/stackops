from __future__ import annotations

from pathlib import Path

import pytest

from machineconfig.cluster.sessions_managers.windows_terminal import wt_remote as remote_module
from machineconfig.utils.schemas.layouts.layout_types import LayoutConfig, TabConfig


def _make_tabs() -> list[TabConfig]:
    return [{"tabName": "api", "startDir": "~/repo", "command": "python api.py"}]


def _make_layout() -> LayoutConfig:
    return {"layoutName": "RemoteLayout", "layoutTabs": _make_tabs()}


class FakeRemoteExecutor:
    def __init__(self, remote_name: str) -> None:
        self.remote_name: str = remote_name


class FakeProcessMonitor:
    def __init__(self, remote_executor: FakeRemoteExecutor) -> None:
        self.remote_executor: FakeRemoteExecutor = remote_executor


class FakeSessionManager:
    def __init__(self, remote_executor: FakeRemoteExecutor, session_name: str, tmp_layout_dir: Path) -> None:
        self.remote_executor: FakeRemoteExecutor = remote_executor
        self.session_name: str = session_name
        self.tmp_layout_dir: Path = tmp_layout_dir


class FakeStatusReporter:
    def __init__(self, process_monitor: FakeProcessMonitor, session_manager: FakeSessionManager) -> None:
        self.process_monitor: FakeProcessMonitor = process_monitor
        self.session_manager: FakeSessionManager = session_manager


class FakeLayoutGenerator:
    @staticmethod
    def generate_random_suffix(length: int) -> str:
        assert length == 8
        return "fixed123"

    def create_wt_script(self, tabs: list[TabConfig], session_name: str, window_name: str | None) -> str:
        assert window_name is None
        return f"script for {session_name} with {len(tabs)} tab(s)"


def test_create_layout_file_writes_script_and_sets_absolute_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(remote_module, "WTRemoteExecutor", FakeRemoteExecutor)
    monkeypatch.setattr(remote_module, "WTProcessMonitor", FakeProcessMonitor)
    monkeypatch.setattr(remote_module, "WTSessionManager", FakeSessionManager)
    monkeypatch.setattr(remote_module, "WTStatusReporter", FakeStatusReporter)
    monkeypatch.setattr(remote_module, "WTLayoutGenerator", FakeLayoutGenerator)
    monkeypatch.setattr(remote_module.Path, "home", lambda: tmp_path)

    generator = remote_module.WTRemoteLayoutGenerator(layout_config=_make_layout(), remote_name="server-a", session_name="sess-a")

    result = generator.create_layout_file()
    script_path = Path(generator.script_path or "")

    assert result is True
    assert script_path.is_file()
    assert script_path.read_text(encoding="utf-8") == "script for sess-a with 1 tab(s)"
    assert script_path.parent == tmp_path / "tmp_results" / "wt_layouts" / "remote"


def test_to_json_and_from_json_round_trip(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(remote_module, "WTRemoteExecutor", FakeRemoteExecutor)
    monkeypatch.setattr(remote_module, "WTProcessMonitor", FakeProcessMonitor)
    monkeypatch.setattr(remote_module, "WTSessionManager", FakeSessionManager)
    monkeypatch.setattr(remote_module, "WTStatusReporter", FakeStatusReporter)
    monkeypatch.setattr(remote_module, "WTLayoutGenerator", FakeLayoutGenerator)
    monkeypatch.setattr(remote_module.Path, "home", lambda: tmp_path)

    generator = remote_module.WTRemoteLayoutGenerator(layout_config=_make_layout(), remote_name="server-a", session_name="sess-a")
    generator.script_path = "/tmp/script.ps1"

    saved_path = generator.to_json(str(tmp_path / "saved" / "remote_session"))
    loaded = remote_module.WTRemoteLayoutGenerator.from_json(str(tmp_path / "saved" / "remote_session"))

    assert saved_path.endswith(".json")
    assert Path(saved_path).is_file()
    assert loaded.remote_name == "server-a"
    assert loaded.session_name == "sess-a"
    assert loaded.layout_config["layoutName"] == "RemoteLayout"
    assert loaded.script_path == "/tmp/script.ps1"


def test_from_json_requires_existing_file_and_list_saved_sessions_is_sorted(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(remote_module, "WTRemoteExecutor", FakeRemoteExecutor)
    monkeypatch.setattr(remote_module, "WTProcessMonitor", FakeProcessMonitor)
    monkeypatch.setattr(remote_module, "WTSessionManager", FakeSessionManager)
    monkeypatch.setattr(remote_module, "WTStatusReporter", FakeStatusReporter)
    monkeypatch.setattr(remote_module, "WTLayoutGenerator", FakeLayoutGenerator)
    monkeypatch.setattr(remote_module.Path, "home", lambda: tmp_path)

    with pytest.raises(FileNotFoundError, match="JSON file not found"):
        remote_module.WTRemoteLayoutGenerator.from_json(str(tmp_path / "missing" / "session"))

    default_dir = tmp_path / "tmp_results" / "wt_sessions" / "serialized"
    default_dir.mkdir(parents=True)
    (default_dir / "b.json").write_text("{}", encoding="utf-8")
    (default_dir / "a.json").write_text("{}", encoding="utf-8")

    custom_dir = tmp_path / "custom"
    custom_dir.mkdir()
    (custom_dir / "z.json").write_text("{}", encoding="utf-8")

    assert remote_module.WTRemoteLayoutGenerator.list_saved_sessions(None) == ["a.json", "b.json"]
    assert remote_module.WTRemoteLayoutGenerator.list_saved_sessions(str(custom_dir)) == ["z.json"]
