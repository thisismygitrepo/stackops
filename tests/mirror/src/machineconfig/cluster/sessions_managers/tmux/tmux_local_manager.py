from dataclasses import dataclass
from typing import ClassVar
import subprocess

import pytest

from machineconfig.cluster.sessions_managers.tmux import tmux_local_manager
from machineconfig.cluster.sessions_managers.session_exit_mode import SessionExitMode
from machineconfig.utils.schemas.layouts.layout_types import LayoutConfig


def _layout(name: str) -> LayoutConfig:
    return {
        "layoutName": name,
        "layoutTabs": [
            {"tabName": "editor", "startDir": "/work/app", "command": "nvim"},
        ],
    }


@dataclass
class _FakeGenerator:
    layout_config: LayoutConfig
    session_name: str
    exit_mode: SessionExitMode
    script_path: str | None = "/tmp/generated.sh"

    created_sessions: ClassVar[list[str]] = []
    failing_sessions: ClassVar[set[str]] = set()

    def create_layout_file(self) -> bool:
        self.created_sessions.append(self.session_name)
        return True

    def apply_launch_plan(self, launch_plan: dict[str, object], on_conflict: str) -> None:
        _ = on_conflict
        if self.session_name in self.failing_sessions:
            raise RuntimeError("apply failed")
        self.session_name = str(launch_plan["session_name"])


def test_init_builds_prefixed_generators(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _FakeGenerator.created_sessions = []
    monkeypatch.setattr(tmux_local_manager, "TmuxLayoutGenerator", _FakeGenerator)

    manager = tmux_local_manager.TmuxLocalManager(
        session_layouts=[_layout("alpha one"), _layout("beta")],
        session_name_prefix="pref",
        exit_mode="backToShell",
    )

    assert manager.get_all_session_names() == ["pref_alpha_one", "pref_beta"]
    assert _FakeGenerator.created_sessions == ["pref_alpha_one", "pref_beta"]


def test_start_all_sessions_collects_success_missing_script_and_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _FakeGenerator.created_sessions = []
    _FakeGenerator.failing_sessions = {"three"}
    monkeypatch.setattr(tmux_local_manager, "TmuxLayoutGenerator", _FakeGenerator)
    manager = tmux_local_manager.TmuxLocalManager(
        session_layouts=[_layout("one"), _layout("two"), _layout("three")],
        session_name_prefix=None,
        exit_mode="backToShell",
    )
    manager.managers[1].script_path = None

    def fake_build_session_launch_plan(
        requested_session_names: list[str],
        backend: str,
        on_conflict: str,
    ) -> list[dict[str, object]]:
        _ = requested_session_names, backend, on_conflict
        return [
            {"requested_name": "one", "session_name": "one", "restart_required": False},
            {"requested_name": "two", "session_name": "two", "restart_required": False},
            {"requested_name": "three", "session_name": "three", "restart_required": False},
        ]

    def fake_run(
        args: list[str],
        capture_output: bool,
        text: bool,
        timeout: int,
    ) -> subprocess.CompletedProcess[str]:
        _ = capture_output, text, timeout
        assert args == ["bash", "/tmp/generated.sh"]
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(
        tmux_local_manager,
        "build_session_launch_plan",
        fake_build_session_launch_plan,
    )
    monkeypatch.setattr(tmux_local_manager.subprocess, "run", fake_run)

    results = manager.start_all_sessions(on_conflict="error")

    assert results["one"] == {
        "success": True,
        "message": "Session 'one' started successfully",
    }
    assert results["two"] == {
        "success": False,
        "error": "No script file path available",
    }
    assert results["three"] == {
        "success": False,
        "error": "apply failed",
    }


def test_attach_to_session_formats_all_commands_and_validates_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _FakeGenerator.created_sessions = []
    monkeypatch.setattr(tmux_local_manager, "TmuxLayoutGenerator", _FakeGenerator)
    manager = tmux_local_manager.TmuxLocalManager(
        session_layouts=[_layout("one"), _layout("two")],
        session_name_prefix=None,
        exit_mode="backToShell",
    )

    def fake_attach_command(session_name: str) -> str:
        return f"attach {session_name}"

    monkeypatch.setattr(
        tmux_local_manager,
        "build_tmux_attach_or_switch_command",
        fake_attach_command,
    )

    output = manager.attach_to_session(session_name=None)

    assert "# Attach to session 'one':" in output
    assert "attach one" in output
    assert "# Attach to session 'two':" in output
    with pytest.raises(ValueError, match="not found"):
        manager.attach_to_session(session_name="missing")


def test_check_all_sessions_status_and_global_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _FakeGenerator.created_sessions = []
    monkeypatch.setattr(tmux_local_manager, "TmuxLayoutGenerator", _FakeGenerator)
    manager = tmux_local_manager.TmuxLocalManager(
        session_layouts=[_layout("one")],
        session_name_prefix=None,
        exit_mode="backToShell",
    )

    def fake_check_tmux_session_status(
        session_name: str,
    ) -> dict[str, object]:
        return {
            "tmux_running": True,
            "session_exists": True,
            "session_name": session_name,
            "all_sessions": [session_name],
        }

    def fake_build_unknown_command_status(tab: dict[str, str]) -> dict[str, object]:
        return {
            "running": False,
            "command": tab["command"],
            "tab_name": tab["tabName"],
            "cwd": tab["startDir"],
        }

    def fake_calculate_global_summary_from_status(
        all_status: dict[str, object],
        include_remote_machines: bool,
    ) -> dict[str, object]:
        assert include_remote_machines is False
        return {
            "total_sessions": len(all_status),
            "healthy_sessions": 1,
            "total_commands": 1,
            "running_commands": 0,
            "all_sessions_healthy": True,
        }

    monkeypatch.setattr(
        tmux_local_manager,
        "check_tmux_session_status",
        fake_check_tmux_session_status,
    )
    monkeypatch.setattr(
        tmux_local_manager,
        "build_unknown_command_status",
        fake_build_unknown_command_status,
    )
    monkeypatch.setattr(
        tmux_local_manager,
        "calculate_global_summary_from_status",
        fake_calculate_global_summary_from_status,
    )

    all_status = manager.check_all_sessions_status()
    global_summary = manager.get_global_summary()

    assert all_status["one"]["summary"] == {
        "total_commands": 1,
        "running_commands": 0,
        "stopped_commands": 1,
        "session_healthy": True,
    }
    assert global_summary["total_sessions"] == 1
