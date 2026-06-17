import pytest

from stackops.scripts.python.helpers.helpers_sessions import session_trace_herdr, sessions_trace


def test_resolve_trace_backend_accepts_herdr_alias() -> None:
    assert sessions_trace.resolve_trace_backend("tmux") == "tmux"
    assert sessions_trace.resolve_trace_backend("t") == "tmux"
    assert sessions_trace.resolve_trace_backend("herdr") == "herdr"
    assert sessions_trace.resolve_trace_backend("h") == "herdr"


def test_evaluate_trace_snapshot_maps_herdr_agent_statuses() -> None:
    snapshot = session_trace_herdr.evaluate_trace_snapshot(
        session_name="build",
        tabs=[
            {"tab_id": "w1:t1", "label": "idle", "number": 1},
            {"tab_id": "w1:t2", "label": "done", "number": 2},
            {"tab_id": "w1:t3", "label": "working", "number": 3},
        ],
        panes=[
            {"pane_id": "w1:p1", "tab_id": "w1:t1", "agent": "codex", "agent_status": "idle"},
            {"pane_id": "w1:p2", "tab_id": "w1:t2", "agent": "codex", "agent_status": "done"},
            {"pane_id": "w1:p3", "tab_id": "w1:t3", "agent": "codex", "agent_status": "working"},
        ],
        until="idle-shell",
        expected_exit_code=None,
        pane_warning=None,
    )

    assert snapshot.session_exists is True
    assert snapshot.total_windows == 3
    assert snapshot.total_targets == 3
    assert snapshot.matched_targets == 2
    assert snapshot.criterion_satisfied is False
    assert snapshot.idle_shell_panes == 1
    assert snapshot.exited_panes == 1
    assert snapshot.running_panes == 1


def test_evaluate_trace_snapshot_supports_herdr_exit_code_fields() -> None:
    snapshot = session_trace_herdr.evaluate_trace_snapshot(
        session_name="build",
        tabs=[{"tab_id": "w1:t1", "label": "done", "number": 1}],
        panes=[
            {
                "pane_id": "w1:p1",
                "tab_id": "w1:t1",
                "agent": "codex",
                "agent_status": "done",
                "exit_code": 0,
            }
        ],
        until="exit-code",
        expected_exit_code=0,
        pane_warning=None,
    )

    assert snapshot.criterion_satisfied is True
    assert snapshot.matched_targets == 1
    assert snapshot.panes[0].status_text == "exited (code 0)"


def test_load_trace_snapshot_uses_workspace_label(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        session_trace_herdr,
        "_load_workspaces",
        lambda: ([{"workspace_id": "w1", "label": "build"}], None),
    )
    monkeypatch.setattr(
        session_trace_herdr,
        "_load_tabs",
        lambda workspace_id: ([{"tab_id": f"{workspace_id}:t1", "label": "agent", "number": 1}], None),
    )
    monkeypatch.setattr(
        session_trace_herdr,
        "_load_panes",
        lambda workspace_id: (
            [{"pane_id": f"{workspace_id}:p1", "tab_id": f"{workspace_id}:t1", "agent_status": "done"}],
            None,
        ),
    )

    snapshot = session_trace_herdr.load_trace_snapshot(
        session_name="build",
        until="all-exited",
        expected_exit_code=None,
    )

    assert snapshot.session_exists is True
    assert snapshot.criterion_satisfied is True
    assert snapshot.total_windows == 1


def test_load_trace_snapshot_treats_missing_workspace_as_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        session_trace_herdr,
        "_load_workspaces",
        lambda: ([{"workspace_id": "w1", "label": "other"}], None),
    )

    snapshot = session_trace_herdr.load_trace_snapshot(
        session_name="build",
        until="session-missing",
        expected_exit_code=None,
    )

    assert snapshot.session_exists is False
    assert snapshot.criterion_satisfied is True
