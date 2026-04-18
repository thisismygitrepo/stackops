from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, cast

import pytest

from stackops.cluster.sessions_managers.zellij.zellij_utils import zellij_local_manager_helper as helper

if TYPE_CHECKING:
    from stackops.cluster.sessions_managers.zellij.zellij_local import ZellijLayoutGenerator
    from stackops.utils.schemas.layouts.layout_types import LayoutConfig

type LayoutConfigLike = dict[str, list[dict[str, str]]]


class FakeManagedManager:
    def __init__(self, session_name: str, layout_config: LayoutConfigLike | None, layout_path: str | None) -> None:
        self.session_name = session_name
        self.layout_config = layout_config
        self.layout_path = layout_path


class FakeLoadedManager:
    def __init__(self, layout_config: LayoutConfigLike | None, session_name: str) -> None:
        self.layout_config = layout_config
        self.session_name = session_name
        self.layout_path: str | None = None


def test_list_saved_sessions_and_delete_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(helper, "TMP_SERIALIZATION_DIR", tmp_path)

    (tmp_path / "zulu").mkdir()
    (tmp_path / "zulu" / "metadata.json").write_text("{}", encoding="utf-8")
    (tmp_path / "alpha").mkdir()
    (tmp_path / "alpha" / "metadata.json").write_text("{}", encoding="utf-8")
    (tmp_path / "ignored").mkdir()

    assert helper.list_saved_sessions() == ["alpha", "zulu"]
    assert helper.delete_session("alpha") is True
    assert (tmp_path / "alpha").exists() is False
    assert helper.delete_session("missing") is False


def test_attach_and_list_active_sessions(monkeypatch: pytest.MonkeyPatch) -> None:
    managers = [
        FakeManagedManager(
            session_name="alpha", layout_config={"layoutTabs": [{"tabName": "one"}, {"tabName": "two"}]}, layout_path="/tmp/alpha.kdl"
        ),
        FakeManagedManager(session_name="beta", layout_config=None, layout_path="/tmp/beta.kdl"),
    ]
    typed_managers = cast("list[ZellijLayoutGenerator]", managers)

    assert helper.attach_to_session(typed_managers, "alpha") == "zellij attach alpha"
    all_commands = helper.attach_to_session(typed_managers, None)
    assert "# Attach to session 'alpha':" in all_commands
    assert "zellij attach beta" in all_commands
    with pytest.raises(ValueError):
        helper.attach_to_session(typed_managers, "missing")

    def fake_run(args: list[str], capture_output: bool, text: bool, timeout: int) -> subprocess.CompletedProcess[str]:
        assert args == ["zellij", "list-sessions"]
        assert capture_output is True
        assert text is True
        assert timeout == 10
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="alpha [Created]\nother [Created]\n", stderr="")

    monkeypatch.setattr(helper.subprocess, "run", fake_run)

    assert helper.list_active_sessions(typed_managers) == [
        {"session_name": "alpha", "is_active": True, "tab_count": 2, "tabs": ["one", "two"]},
        {"session_name": "beta", "is_active": False, "tab_count": 0, "tabs": []},
    ]


def test_save_and_load_manager_round_trip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(helper, "TMP_SERIALIZATION_DIR", tmp_path)

    session_layouts: list[dict[str, object]] = [{"layoutName": "alpha-layout"}, {"layoutName": "beta-layout"}]
    managers = [
        FakeManagedManager(session_name="alpha", layout_config={"layoutTabs": [{"tabName": "main"}]}, layout_path="/tmp/alpha.kdl"),
        FakeManagedManager(session_name="beta", layout_config={"layoutTabs": [{"tabName": "secondary"}]}, layout_path="/tmp/beta.kdl"),
    ]
    typed_session_layouts = cast("list[LayoutConfig]", session_layouts)
    typed_managers = cast("list[ZellijLayoutGenerator]", managers)

    session_id = helper.save_manager(typed_session_layouts, typed_managers, session_name_prefix="demo", session_id="sess-1234")
    assert session_id == "sess-1234"
    assert (tmp_path / "sess-1234" / "session_layouts.json").exists() is True
    assert (tmp_path / "sess-1234" / "metadata.json").exists() is True
    assert (tmp_path / "sess-1234" / "managers" / "manager_0_alpha.json").exists() is True

    fake_module = ModuleType("stackops.cluster.sessions_managers.zellij.zellij_local")
    setattr(fake_module, "ZellijLayoutGenerator", FakeLoadedManager)
    monkeypatch.setitem(sys.modules, "stackops.cluster.sessions_managers.zellij.zellij_local", fake_module)

    loaded_layouts, loaded_managers = helper.load_manager("sess-1234")

    assert loaded_layouts == session_layouts
    assert [manager.session_name for manager in loaded_managers] == ["alpha", "beta"]
    assert [manager.layout_path for manager in loaded_managers] == ["/tmp/alpha.kdl", "/tmp/beta.kdl"]


def test_kill_all_sessions_collects_success_and_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    managers = [
        FakeManagedManager(session_name="alpha", layout_config=None, layout_path="/tmp/alpha.kdl"),
        FakeManagedManager(session_name="broken", layout_config=None, layout_path="/tmp/broken.kdl"),
    ]
    typed_managers = cast("list[ZellijLayoutGenerator]", managers)

    def fake_run(command: str, shell: bool, capture_output: bool, text: bool, timeout: int) -> subprocess.CompletedProcess[str]:
        assert shell is True
        assert capture_output is True
        assert text is True
        assert timeout == 10
        if "broken" in command:
            raise RuntimeError("boom")
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(helper.subprocess, "run", fake_run)

    assert helper.kill_all_sessions(typed_managers) == {
        "alpha": {"success": True, "message": "Session killed"},
        "broken": {"success": False, "error": "boom"},
    }
