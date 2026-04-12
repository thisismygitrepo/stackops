from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import pytest

import machineconfig.cluster.sessions_managers.zellij.zellij_remote_manager as zellij_remote_manager
from machineconfig.cluster.sessions_managers.zellij.zellij_remote_manager import (
    ZellijSessionManager,
)
from machineconfig.utils.schemas.layouts.layout_types import LayoutConfig


@dataclass
class _FakeRemoteLayoutGenerator:
    remote_name: str
    session_name: str
    saved_paths: list[str] = field(default_factory=list)

    def to_json(self, file_path: str) -> str:
        self.saved_paths.append(file_path)
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")
        return file_path


@dataclass
class _LoadedManager:
    remote_name: str
    session_name: str


def _build_machine_layouts() -> dict[str, LayoutConfig]:
    return {
        "node-a": {
            "layoutName": "demo",
            "layoutTabs": [
                {
                    "tabName": "api",
                    "startDir": "~/code/api",
                    "command": "uv run api.py",
                }
            ],
        }
    }


def test_ssh_to_all_machines_builds_tab_commands(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = ZellijSessionManager.__new__(ZellijSessionManager)
    manager.managers = [
        _FakeRemoteLayoutGenerator(remote_name="node-a", session_name="sess-a"),
        _FakeRemoteLayoutGenerator(remote_name="node-b", session_name="sess-b"),
    ]

    monkeypatch.setattr(
        zellij_remote_manager,
        "run_command_in_zellij_tab",
        lambda command, tab_name, cwd: f"[{tab_name}] {command} cwd={cwd}",
    )

    result = manager.ssh_to_all_machines()

    assert "[node-a] ssh node-a -t 'zellij attach sess-a' cwd=None" in result
    assert "[node-b] ssh node-b -t 'zellij attach sess-b' cwd=None" in result


def test_save_writes_metadata_and_serializes_managers(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(zellij_remote_manager, "TMP_SERIALIAZATION_DIR", tmp_path)

    manager = ZellijSessionManager.__new__(ZellijSessionManager)
    manager.machine_layouts = _build_machine_layouts()
    manager.session_name_prefix = "JobMgr"
    fake_manager = _FakeRemoteLayoutGenerator(remote_name="node-a", session_name="sess-a")
    manager.managers = [fake_manager]

    session_id = manager.save("session-1")

    session_dir = tmp_path / "session-1"
    metadata = json.loads((session_dir / "metadata.json").read_text(encoding="utf-8"))
    config = json.loads((session_dir / "machine_layouts.json").read_text(encoding="utf-8"))

    assert session_id == "session-1"
    assert config == _build_machine_layouts()
    assert metadata["session_name_prefix"] == "JobMgr"
    assert fake_manager.saved_paths == [
        str(session_dir / "managers" / "manager_0_node-a.json")
    ]


def test_load_reads_saved_managers_from_disk(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    session_dir = tmp_path / "session-1"
    managers_dir = session_dir / "managers"
    managers_dir.mkdir(parents=True)
    (session_dir / "machine_layouts.json").write_text(
        json.dumps(_build_machine_layouts()),
        encoding="utf-8",
    )
    (session_dir / "metadata.json").write_text(
        json.dumps({"session_name_prefix": "LoadedPrefix"}),
        encoding="utf-8",
    )
    (managers_dir / "manager_0_node-a.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(zellij_remote_manager, "TMP_SERIALIAZATION_DIR", tmp_path)

    def fake_init(
        self: ZellijSessionManager,
        machine_layouts: dict[str, LayoutConfig],
        session_name_prefix: str,
    ) -> None:
        self.machine_layouts = machine_layouts
        self.session_name_prefix = session_name_prefix
        self.managers = []

    monkeypatch.setattr(ZellijSessionManager, "__init__", fake_init)
    monkeypatch.setattr(
        zellij_remote_manager.ZellijRemoteLayoutGenerator,
        "from_json",
        staticmethod(lambda file_path: _LoadedManager(remote_name="node-a", session_name="sess-a")),
    )

    loaded = ZellijSessionManager.load("session-1")

    assert loaded.session_name_prefix == "LoadedPrefix"
    assert loaded.machine_layouts == _build_machine_layouts()
    assert loaded.managers == [_LoadedManager(remote_name="node-a", session_name="sess-a")]


def test_delete_session_removes_existing_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    session_dir = tmp_path / "session-1"
    session_dir.mkdir()
    monkeypatch.setattr(zellij_remote_manager, "TMP_SERIALIAZATION_DIR", tmp_path)

    assert ZellijSessionManager.delete_session("session-1") is True
    assert session_dir.exists() is False
    assert ZellijSessionManager.delete_session("missing") is False
