from __future__ import annotations

import subprocess

import pytest

import machineconfig.cluster.sessions_managers.helpers.enhanced_command_runner as runner_module
from machineconfig.cluster.sessions_managers.helpers.enhanced_command_runner import (
    enhanced_zellij_session_start,
    run_enhanced_command,
)
from machineconfig.cluster.sessions_managers.session_conflict import SessionLaunchPlan


def test_run_enhanced_command_returns_success_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    recorded_kwargs: list[dict[str, object]] = []

    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        _ = args
        recorded_kwargs.append(dict(kwargs))
        return subprocess.CompletedProcess(args="echo hi", returncode=0, stdout="hello\n", stderr="")

    monkeypatch.setattr(runner_module.subprocess, "run", fake_run)

    result = run_enhanced_command(command="echo hi", description=None, show_progress=False, timeout=9)

    assert result == {"success": True, "returncode": 0, "stdout": "hello", "stderr": ""}
    assert recorded_kwargs[0]["timeout"] == 9


def test_run_enhanced_command_handles_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        _ = args, kwargs
        raise subprocess.TimeoutExpired(cmd="sleep 1", timeout=5)

    monkeypatch.setattr(runner_module.subprocess, "run", fake_run)

    result = run_enhanced_command(command="sleep 1", description="wait", show_progress=False, timeout=5)

    assert result == {"success": False, "error": "Timeout", "timeout": 5}


def test_enhanced_zellij_session_start_restarts_existing_session(monkeypatch: pytest.MonkeyPatch) -> None:
    killed: list[tuple[str, str]] = []
    captured_commands: list[str] = []

    def fake_build_session_launch_plan(
        requested_session_names: list[str],
        backend: str,
        on_conflict: str,
    ) -> list[SessionLaunchPlan]:
        assert requested_session_names == ["demo"]
        assert backend == "zellij"
        assert on_conflict == "restart"
        return [
            SessionLaunchPlan(
                requested_name="demo",
                session_name="demo-2",
                restart_required=True,
            )
        ]

    def fake_kill_existing_session(backend: str, session_name: str) -> None:
        killed.append((backend, session_name))

    def fake_run_enhanced_command(
        command: str,
        description: str | None,
        show_progress: bool,
        timeout: int | None,
    ) -> dict[str, object]:
        captured_commands.append(command)
        assert description == "Starting session 'demo-2' with layout"
        assert show_progress is False
        assert timeout == 10
        return {"success": True, "returncode": 0, "stdout": "", "stderr": ""}

    monkeypatch.setattr(runner_module, "build_session_launch_plan", fake_build_session_launch_plan)
    monkeypatch.setattr(runner_module, "kill_existing_session", fake_kill_existing_session)
    monkeypatch.setattr(runner_module, "run_enhanced_command", fake_run_enhanced_command)

    result = enhanced_zellij_session_start(
        session_name="demo",
        layout_path="/tmp/layout with spaces.kdl",
        on_conflict="restart",
    )

    assert killed == [("zellij", "demo-2")]
    assert "--layout '/tmp/layout with spaces.kdl'" in captured_commands[0]
    assert captured_commands[0].endswith("a -b demo-2")
    assert result["session_name"] == "demo-2"
