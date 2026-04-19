

import subprocess
from dataclasses import dataclass
from typing import cast

import pytest

import stackops.cluster.sessions_managers.zellij.zellij_local_manager as zellij_local_manager
from stackops.cluster.sessions_managers.zellij.zellij_local_manager import (
    ZellijLocalManager,
)
from stackops.cluster.sessions_managers.zellij.zellij_utils.monitoring_types import (
    SessionReport,
)
from stackops.utils.schemas.layouts.layout_types import LayoutConfig


@dataclass
class _FakeManager:
    session_name: str
    layout_path: str | None


@dataclass
class _LaunchPlan:
    session_name: str
    restart_required: bool


def _completed_process(stdout: str) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=["zellij"], returncode=0, stdout=stdout, stderr="")


def test_update_runtime_tracker_accumulates_only_running_tabs() -> None:
    all_status = cast(
        dict[str, SessionReport],
        {
            "alpha": {
                "session_status": {"zellij_running": True, "session_exists": True, "session_name": "alpha", "all_sessions": []},
                "commands_status": {
                    "api": {"running": True, "status": "running", "processes": [], "command": "api", "tab_name": "api"},
                    "worker": {"running": False, "status": "not_running", "processes": [], "command": "worker", "tab_name": "worker"},
                },
                "summary": {
                    "total_commands": 2,
                    "running_commands": 1,
                    "stopped_commands": 1,
                    "session_healthy": True,
                },
            }
        },
    )
    runtime_seconds_by_key: dict[tuple[str, str], float] = {("alpha", "api"): 5.0}

    zellij_local_manager._update_runtime_tracker(all_status, runtime_seconds_by_key, elapsed_seconds=2.5)

    assert runtime_seconds_by_key == {
        ("alpha", "api"): 7.5,
        ("alpha", "worker"): 0.0,
    }


def test_build_global_summary_counts_across_sessions() -> None:
    all_status = cast(
        dict[str, SessionReport],
        {
            "alpha": {
                "session_status": {"zellij_running": True, "session_exists": True, "session_name": "alpha", "all_sessions": []},
                "commands_status": {},
                "summary": {
                    "total_commands": 2,
                    "running_commands": 1,
                    "stopped_commands": 1,
                    "session_healthy": True,
                },
            },
            "beta": {
                "session_status": {"zellij_running": True, "session_exists": False, "session_name": "beta", "all_sessions": []},
                "commands_status": {},
                "summary": {
                    "total_commands": 3,
                    "running_commands": 2,
                    "stopped_commands": 1,
                    "session_healthy": False,
                },
            },
        },
    )

    summary = zellij_local_manager._build_global_summary(all_status)

    assert summary == {
        "total_sessions": 2,
        "healthy_sessions": 1,
        "unhealthy_sessions": 1,
        "total_commands": 5,
        "running_commands": 3,
        "stopped_commands": 2,
        "all_sessions_healthy": False,
        "all_commands_running": False,
    }


def test_start_all_sessions_renames_restart_and_polls_until_visible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started_commands: list[list[str]] = []
    killed_sessions: list[tuple[str, str]] = []
    manager = cast(ZellijLocalManager, ZellijLocalManager.__new__(ZellijLocalManager))
    manager.managers = [_FakeManager(session_name="alpha", layout_path="/tmp/layout.kdl")]

    monkeypatch.setattr(
        zellij_local_manager,
        "build_session_launch_plan",
        lambda requested_session_names, backend, on_conflict: [
            {"session_name": "alpha_1", "restart_required": True}
        ],
    )
    monkeypatch.setattr(
        zellij_local_manager,
        "kill_existing_session",
        lambda backend, session_name: killed_sessions.append((backend, session_name)),
    )
    monkeypatch.setattr(zellij_local_manager.console, "print", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        zellij_local_manager.subprocess,
        "Popen",
        lambda command: started_commands.append(command),
    )
    monkeypatch.setattr(
        zellij_local_manager.subprocess,
        "run",
        lambda command, capture_output, text: _completed_process("alpha_1\n"),
    )
    monkeypatch.setattr(zellij_local_manager.time, "sleep", lambda _: None)

    result = manager.start_all_sessions(
        on_conflict="error",
        poll_seconds=1.0,
        poll_interval=0.01,
    )

    assert killed_sessions == [("zellij", "alpha_1")]
    assert started_commands == [
        [
            "bash",
            "-lc",
            "ZELLIJ_AUTO_ATTACH=0 zellij --layout /tmp/layout.kdl attach alpha_1 --create >/dev/null 2>&1 &",
        ]
    ]
    assert manager.managers[0].session_name == "alpha_1"
    assert result == {"alpha_1": {"success": True, "message": "Session 'alpha_1' started"}}


def test_save_and_static_helpers_delegate_to_helper_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = cast(ZellijLocalManager, ZellijLocalManager.__new__(ZellijLocalManager))
    manager.session_layouts = cast(list[LayoutConfig], [{"layoutName": "demo", "layoutTabs": []}])
    manager.managers = []
    manager.session_name_prefix = "LocalJobMgr"
    captured_save_args: list[tuple[object, object, object, object]] = []

    def fake_save_manager(
        session_layouts: list[LayoutConfig],
        managers: list[object],
        session_name_prefix: str,
        session_id: str | None,
    ) -> str:
        captured_save_args.append((session_layouts, managers, session_name_prefix, session_id))
        return "saved-1"

    monkeypatch.setattr(zellij_local_manager.helper, "save_manager", fake_save_manager)
    monkeypatch.setattr(zellij_local_manager.helper, "list_saved_sessions", lambda: ["saved-1", "saved-2"])
    monkeypatch.setattr(zellij_local_manager.helper, "delete_session", lambda session_id: session_id == "saved-1")

    assert manager.save(None) == "saved-1"
    assert captured_save_args == [([{"layoutName": "demo", "layoutTabs": []}], [], "LocalJobMgr", None)]
    assert ZellijLocalManager.list_saved_sessions() == ["saved-1", "saved-2"]
    assert ZellijLocalManager.delete_session("saved-1") is True
