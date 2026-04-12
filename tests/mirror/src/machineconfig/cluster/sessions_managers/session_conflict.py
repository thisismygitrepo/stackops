import json
import subprocess
import sys
from types import ModuleType

import pytest

from machineconfig.cluster.sessions_managers import session_conflict


def test_list_existing_sessions_windows_terminal_parses_titles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_helpers = ModuleType("wt_helpers")
    setattr(fake_helpers, "POWERSHELL_CMD", "pwsh")
    monkeypatch.setitem(
        sys.modules,
        "machineconfig.cluster.sessions_managers.windows_terminal.wt_utils.wt_helpers",
        fake_helpers,
    )

    def fake_run(
        args: list[str],
        capture_output: bool,
        text: bool,
        timeout: int,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        _ = capture_output, text, timeout, check
        assert args[0:2] == ["pwsh", "-Command"]
        assert isinstance(args[2], str)
        payload = [
            {"MainWindowTitle": "Alpha"},
            {"MainWindowTitle": "  "},
            {"MainWindowTitle": "Beta - shell"},
        ]
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=json.dumps(payload),
            stderr="",
        )

    monkeypatch.setattr(session_conflict.subprocess, "run", fake_run)

    assert session_conflict.list_existing_sessions("windows-terminal") == {
        "Alpha",
        "Beta - shell",
    }


def test_session_exists_windows_terminal_matches_casefolded_substrings() -> None:
    existing_sessions = {"ALPHA", "Beta Project"}

    assert session_conflict.session_exists(
        session_name="alpha",
        existing_sessions=existing_sessions,
        backend="windows-terminal",
    )
    assert session_conflict.session_exists(
        session_name="project",
        existing_sessions=existing_sessions,
        backend="windows-terminal",
    )
    assert not session_conflict.session_exists(
        session_name="gamma",
        existing_sessions=existing_sessions,
        backend="windows-terminal",
    )


def test_build_session_launch_plan_rename_uses_next_free_suffix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_list_existing_sessions(
        _backend: session_conflict.SessionBackend,
    ) -> set[str]:
        return {"alpha_1"}

    monkeypatch.setattr(
        session_conflict,
        "list_existing_sessions",
        fake_list_existing_sessions,
    )

    plans = session_conflict.build_session_launch_plan(
        requested_session_names=["alpha", "alpha"],
        backend="tmux",
        on_conflict="rename",
    )

    assert plans == [
        {
            "requested_name": "alpha",
            "session_name": "alpha",
            "restart_required": False,
        },
        {
            "requested_name": "alpha",
            "session_name": "alpha_2",
            "restart_required": False,
            "conflict_source": "duplicate",
        },
    ]


def test_build_session_launch_plan_windows_terminal_skip_marks_existing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_list_existing_sessions(
        _backend: session_conflict.SessionBackend,
    ) -> set[str]:
        return {"main"}

    monkeypatch.setattr(
        session_conflict,
        "list_existing_sessions",
        fake_list_existing_sessions,
    )

    plans = session_conflict.build_session_launch_plan(
        requested_session_names=["main", "other"],
        backend="windows-terminal",
        on_conflict="mergeNewWindowsSkipMatchingWindows",
    )

    assert plans[0] == {
        "requested_name": "main",
        "session_name": "main",
        "restart_required": False,
        "conflict_source": "existing",
        "skip_launch": True,
    }
    assert plans[1] == {
        "requested_name": "other",
        "session_name": "other",
        "restart_required": False,
    }


def test_build_session_launch_plan_windows_terminal_overwrite_restarts_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_list_existing_sessions(
        _backend: session_conflict.SessionBackend,
    ) -> set[str]:
        return {"main"}

    monkeypatch.setattr(
        session_conflict,
        "list_existing_sessions",
        fake_list_existing_sessions,
    )

    plans = session_conflict.build_session_launch_plan(
        requested_session_names=["main", "main"],
        backend="windows-terminal",
        on_conflict="mergeNewWindowsOverwriteMatchingWindows",
    )

    assert plans[0]["restart_required"] is True
    assert plans[0]["conflict_source"] == "existing"
    assert plans[1]["restart_required"] is False
    assert plans[1]["conflict_source"] == "duplicate"


def test_build_session_launch_plan_rejects_merge_on_unsupported_backend() -> None:
    with pytest.raises(ValueError, match="only supported"):
        session_conflict.build_session_launch_plan(
            requested_session_names=["main"],
            backend="zellij",
            on_conflict="mergeNewWindowsSkipMatchingWindows",
        )


def test_kill_existing_session_tmux_invokes_expected_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run(
        args: list[str],
        capture_output: bool,
        text: bool,
        timeout: int,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        _ = capture_output, text, timeout, check
        calls.append(args)
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(session_conflict.subprocess, "run", fake_run)

    session_conflict.kill_existing_session("tmux", "alpha")

    assert calls == [["tmux", "kill-session", "-t", "alpha"]]
