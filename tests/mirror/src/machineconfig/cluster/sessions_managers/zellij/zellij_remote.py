from __future__ import annotations

from pathlib import Path

import pytest

import machineconfig.cluster.sessions_managers.zellij.zellij_remote as zellij_remote
from machineconfig.cluster.sessions_managers.zellij.zellij_remote import (
    ZellijRemoteLayoutGenerator,
)
from machineconfig.utils.schemas.layouts.layout_types import LayoutConfig


class _FakeRemoteExecutor:
    def __init__(self, remote_name: str) -> None:
        self.remote_name = remote_name


class _FakeLayoutGenerator:
    def create_layout_file(self, layout_config: LayoutConfig, session_name: str) -> str:
        return f"layout::{layout_config['layoutName']}::{session_name}"


class _FakeProcessMonitor:
    def __init__(self, remote_executor: _FakeRemoteExecutor) -> None:
        self.location_name = remote_executor.remote_name


class _FakeSessionManager:
    def __init__(self, remote_executor: _FakeRemoteExecutor, session_name: str, tmp_layout_dir: Path) -> None:
        self.remote_executor = remote_executor
        self.session_name = session_name
        self.tmp_layout_dir = tmp_layout_dir


class _FakeStatusReporter:
    def __init__(self, process_monitor: _FakeProcessMonitor, session_manager: _FakeSessionManager) -> None:
        self.process_monitor = process_monitor
        self.session_manager = session_manager


def _build_layout_config() -> LayoutConfig:
    return {
        "layoutName": "remote-demo",
        "layoutTabs": [
            {
                "tabName": "api",
                "startDir": "~/code/api",
                "command": "uv run api.py",
            }
        ],
    }


def _patch_remote_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(zellij_remote, "RemoteExecutor", _FakeRemoteExecutor)
    monkeypatch.setattr(zellij_remote, "LayoutGenerator", _FakeLayoutGenerator)
    monkeypatch.setattr(zellij_remote, "ProcessMonitor", _FakeProcessMonitor)
    monkeypatch.setattr(zellij_remote, "SessionManager", _FakeSessionManager)
    monkeypatch.setattr(zellij_remote, "StatusReporter", _FakeStatusReporter)
    monkeypatch.setattr(zellij_remote.console, "print", lambda *args, **kwargs: None)


def test_create_layout_file_writes_generated_content(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _patch_remote_dependencies(monkeypatch)
    monkeypatch.setattr(zellij_remote, "TMP_LAYOUT_DIR", tmp_path)

    generator = ZellijRemoteLayoutGenerator(
        layout_config=_build_layout_config(),
        remote_name="node-a",
        session_name="alpha",
    )

    created = generator.create_layout_file()

    assert created is True
    assert generator.layout_path is not None
    layout_path = Path(generator.layout_path)
    assert layout_path.read_text(encoding="utf-8") == "layout::remote-demo::alpha"
    assert layout_path == tmp_path / "zellij_layout_alpha.kdl"


def test_to_json_and_from_json_round_trip(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fake_home() -> Path:
        return tmp_path

    _patch_remote_dependencies(monkeypatch)
    monkeypatch.setattr(zellij_remote.Path, "home", staticmethod(fake_home))

    generator = ZellijRemoteLayoutGenerator(
        layout_config=_build_layout_config(),
        remote_name="node-a",
        session_name="alpha",
    )
    generator.layout_path = "/tmp/layout.kdl"

    saved_path = generator.to_json(None)
    loaded = ZellijRemoteLayoutGenerator.from_json(saved_path)

    assert Path(saved_path).suffix == ".json"
    assert Path(saved_path).is_file()
    assert loaded.remote_name == "node-a"
    assert loaded.session_name == "alpha"
    assert loaded.layout_path == "/tmp/layout.kdl"


def test_list_saved_sessions_returns_sorted_json_names(tmp_path: Path) -> None:
    (tmp_path / "b.json").write_text("{}", encoding="utf-8")
    (tmp_path / "a.json").write_text("{}", encoding="utf-8")
    (tmp_path / "ignore.txt").write_text("x", encoding="utf-8")

    assert ZellijRemoteLayoutGenerator.list_saved_sessions(tmp_path) == ["a.json", "b.json"]
