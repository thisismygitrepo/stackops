

from typing import ClassVar

import pytest

from stackops.cluster.sessions_managers.session_exit_mode import SessionExitMode
from stackops.cluster.sessions_managers.windows_terminal.wt_utils.examples import wt_local_manager_demo as demo_module
from stackops.utils.schemas.layouts.layout_types import LayoutConfig


class FakeWTLocalManager:
    init_layouts: ClassVar[list[LayoutConfig] | None] = None
    init_prefix: ClassVar[str | None] = None
    init_exit_mode: ClassVar[SessionExitMode | None] = None
    last_loaded_session_id: ClassVar[str | None] = None

    def __init__(self, session_layouts: list[LayoutConfig], session_name_prefix: str | None, exit_mode: SessionExitMode) -> None:
        self.__class__.init_layouts = session_layouts
        self.__class__.init_prefix = session_name_prefix
        self.__class__.init_exit_mode = exit_mode
        self.managers: list[object] = [{}, {}, {}]

    def get_all_session_names(self) -> list[str]:
        return ["DevelopmentEnv", "TestingEnv", "DeploymentEnv"]

    def attach_to_session(self) -> str:
        return "wt -w DevelopmentEnv"

    def print_status_report(self) -> None:
        print("status report")

    def get_wt_overview(self) -> dict[str, object]:
        return {"success": True, "total_windows": 2, "managed_sessions": 3}

    def save(self) -> str:
        return "saved-demo"

    @staticmethod
    def list_saved_sessions() -> list[str]:
        return ["saved-demo"]

    @classmethod
    def load(cls, session_id: str) -> "FakeWTLocalManager":
        cls.last_loaded_session_id = session_id
        instance = cls.__new__(cls)
        instance.managers = [{}, {}, {}]
        return instance


def test_run_demo_uses_manager_api_and_prints_summary(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(demo_module, "WTLocalManager", FakeWTLocalManager)

    demo_module.run_demo()
    output = capsys.readouterr().out

    assert FakeWTLocalManager.init_layouts is not None
    assert len(FakeWTLocalManager.init_layouts) == 3
    assert FakeWTLocalManager.init_prefix == "DevEnv"
    assert FakeWTLocalManager.init_exit_mode == "backToShell"
    assert FakeWTLocalManager.last_loaded_session_id == "saved-demo"
    assert "Local manager created with 3 sessions" in output
    assert "Saved session: saved-demo" in output
    assert "Loaded session with 3 sessions" in output
