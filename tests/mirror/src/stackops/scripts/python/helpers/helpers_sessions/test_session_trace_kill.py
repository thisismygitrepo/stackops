import subprocess

import pytest

from stackops.scripts.python.helpers.helpers_sessions import session_trace_kill
from stackops.scripts.python.helpers.helpers_sessions.session_trace_models import (
    TracePaneState,
    TraceSnapshot,
    build_missing_snapshot,
)


def _pane(
    window_name: str,
    window_target: str,
    pane_target: str,
    matched: bool,
) -> TracePaneState:
    return TracePaneState(
        window_index=window_target,
        window_name=window_name,
        window_target=window_target,
        pane_index=pane_target,
        pane_target=pane_target,
        process_name="shell" if matched else "python",
        status_text="idle shell" if matched else "running: python",
        cwd="/work",
        is_active=False,
        category="idle-shell" if matched else "running",
        exit_code=None,
        matched=matched,
    )


def _snapshot(
    session_name: str,
    session_target: str,
    panes: tuple[TracePaneState, ...],
    criterion_satisfied: bool,
) -> TraceSnapshot:
    matched_targets = sum(pane.matched for pane in panes)
    window_targets = {pane.window_target for pane in panes}
    return TraceSnapshot(
        session_name=session_name,
        session_target=session_target,
        session_exists=True,
        total_windows=len(window_targets),
        panes=panes,
        total_targets=len(panes),
        matched_targets=matched_targets,
        pane_warning=None,
        session_error=None,
        criterion_satisfied=criterion_satisfied,
        idle_shell_panes=matched_targets,
        running_panes=len(panes) - matched_targets,
        exited_panes=0,
        unknown_panes=0,
    )


def test_tmux_plan_collapses_matched_panes_to_windows_and_sessions() -> None:
    partial_snapshot = _snapshot(
        session_name="build",
        session_target="build",
        panes=(
            _pane(window_name="ready", window_target="@1", pane_target="%1", matched=True),
            _pane(window_name="ready", window_target="@1", pane_target="%2", matched=True),
            _pane(window_name="mixed", window_target="@2", pane_target="%3", matched=True),
            _pane(window_name="mixed", window_target="@2", pane_target="%4", matched=False),
        ),
        criterion_satisfied=False,
    )

    partial_plan = session_trace_kill.build_trace_kill_plan(
        backend="tmux",
        snapshots=(partial_snapshot,),
    )

    assert [command.argv for command in partial_plan.commands] == [
        ("tmux", "kill-window", "-t", "@1"),
        ("tmux", "kill-pane", "-t", "%3"),
    ]
    assert [command.summary["action"] for command in partial_plan.commands] == ["window", "pane"]
    assert partial_plan.completed_session_names == frozenset()

    complete_plan = session_trace_kill.build_trace_kill_plan(
        backend="tmux",
        snapshots=(
            _snapshot(
                session_name="build",
                session_target="build",
                panes=(_pane(window_name="ready", window_target="@1", pane_target="%1", matched=True),),
                criterion_satisfied=True,
            ),
        ),
    )

    assert [command.argv for command in complete_plan.commands] == [
        ("tmux", "kill-session", "-t", "build"),
    ]
    assert complete_plan.completed_session_names == frozenset({"build"})


def test_herdr_plan_uses_workspace_tab_and_pane_identifiers() -> None:
    partial_snapshot = _snapshot(
        session_name="Build workspace",
        session_target="workspace-1",
        panes=(
            _pane(window_name="ready", window_target="tab-1", pane_target="pane-1", matched=True),
            _pane(window_name="mixed", window_target="tab-2", pane_target="pane-2", matched=True),
            _pane(window_name="mixed", window_target="tab-2", pane_target="pane-3", matched=False),
        ),
        criterion_satisfied=False,
    )

    partial_plan = session_trace_kill.build_trace_kill_plan(
        backend="herdr",
        snapshots=(partial_snapshot,),
    )
    complete_plan = session_trace_kill.build_trace_kill_plan(
        backend="herdr",
        snapshots=(
            _snapshot(
                session_name="Build workspace",
                session_target="workspace-1",
                panes=(_pane(window_name="ready", window_target="tab-1", pane_target="pane-1", matched=True),),
                criterion_satisfied=True,
            ),
        ),
    )

    assert [command.argv for command in partial_plan.commands] == [
        ("herdr", "tab", "close", "tab-1"),
        ("herdr", "pane", "close", "pane-2"),
    ]
    assert [command.argv for command in complete_plan.commands] == [
        ("herdr", "workspace", "close", "workspace-1"),
    ]


def test_aoe_plan_stops_the_canonical_session_identifier() -> None:
    snapshot = _snapshot(
        session_name="Build",
        session_target="session-42",
        panes=(_pane(window_name="Build", window_target="session-42", pane_target="session-42", matched=True),),
        criterion_satisfied=True,
    )

    plan = session_trace_kill.build_trace_kill_plan(backend="aoe", snapshots=(snapshot,))

    assert [command.argv for command in plan.commands] == [
        ("aoe", "session", "stop", "session-42"),
    ]
    assert plan.completed_session_names == frozenset({"Build"})


def test_missing_session_completes_without_a_kill_command() -> None:
    missing_snapshot = build_missing_snapshot(
        session_name="already-gone",
        until="session-missing",
        session_error=None,
    )

    plan = session_trace_kill.build_trace_kill_plan(
        backend="tmux",
        snapshots=(missing_snapshot,),
    )

    assert plan.commands == ()
    assert plan.completed_session_names == frozenset({"already-gone"})


def test_execute_trace_kill_plan_reports_backend_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    plan = session_trace_kill.build_trace_kill_plan(
        backend="tmux",
        snapshots=(
            _snapshot(
                session_name="build",
                session_target="build",
                panes=(_pane(window_name="main", window_target="@1", pane_target="%1", matched=True),),
                criterion_satisfied=True,
            ),
        ),
    )

    def fake_run_command(args: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
        assert timeout == 30.0
        return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="target vanished")

    monkeypatch.setattr(session_trace_kill, "run_command", fake_run_command)

    with pytest.raises(RuntimeError, match="target vanished"):
        session_trace_kill.execute_trace_kill_plan(plan=plan)
