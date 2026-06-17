import pytest

from stackops.scripts.python.helpers.helpers_sessions import session_trace_aoe


def _session(title: str, status: str = "running") -> session_trace_aoe.JsonObject:
    return {
        "title": title,
        "id": f"id-{title}",
        "status": status,
        "agent": "codex",
        "path": "/work/repo",
    }


def test_evaluate_trace_snapshot_maps_aoe_waiting_to_idle() -> None:
    snapshot = session_trace_aoe.evaluate_trace_snapshot(
        session_name="build",
        session=_session("build", "waiting"),
        until="idle-shell",
        expected_exit_code=None,
        pane_warning=None,
    )

    assert snapshot.session_exists is True
    assert snapshot.total_windows == 1
    assert snapshot.total_targets == 1
    assert snapshot.matched_targets == 1
    assert snapshot.criterion_satisfied is True
    assert snapshot.idle_shell_panes == 1
    assert snapshot.panes[0].process_name == "codex"


def test_evaluate_trace_snapshot_maps_aoe_stopped_to_exited() -> None:
    snapshot = session_trace_aoe.evaluate_trace_snapshot(
        session_name="build",
        session=_session("build", "stopped"),
        until="all-exited",
        expected_exit_code=None,
        pane_warning=None,
    )

    assert snapshot.criterion_satisfied is True
    assert snapshot.exited_panes == 1
    assert snapshot.panes[0].status_text == "stopped"


def test_evaluate_trace_snapshot_supports_aoe_exit_code_fields() -> None:
    session = _session("build", "running")
    session["exitCode"] = 0

    snapshot = session_trace_aoe.evaluate_trace_snapshot(
        session_name="build",
        session=session,
        until="exit-code",
        expected_exit_code=0,
        pane_warning=None,
    )

    assert snapshot.criterion_satisfied is True
    assert snapshot.matched_targets == 1
    assert snapshot.panes[0].status_text == "exited (code 0)"


def test_load_trace_snapshot_uses_session_title(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        session_trace_aoe,
        "_session_entries",
        lambda: [_session("build", "stopped")],
    )

    snapshot = session_trace_aoe.load_trace_snapshot(
        session_name="build",
        until="all-exited",
        expected_exit_code=None,
    )

    assert snapshot.session_exists is True
    assert snapshot.criterion_satisfied is True


def test_load_trace_snapshot_treats_missing_session_as_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        session_trace_aoe,
        "_session_entries",
        lambda: [_session("other", "running")],
    )

    snapshot = session_trace_aoe.load_trace_snapshot(
        session_name="build",
        until="session-missing",
        expected_exit_code=None,
    )

    assert snapshot.session_exists is False
    assert snapshot.criterion_satisfied is True
