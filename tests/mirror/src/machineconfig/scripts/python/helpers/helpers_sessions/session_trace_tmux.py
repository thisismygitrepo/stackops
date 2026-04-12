from __future__ import annotations

from typing import cast

import pytest

import machineconfig.scripts.python.helpers.helpers_sessions.session_trace_tmux as subject


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("7", 7),
        (" -2 ", -2),
        ("oops", None),
        ("--1", None),
        ("", None),
    ],
)
def test_parse_exit_code(raw_value: str, expected: int | None) -> None:
    assert subject._parse_exit_code(raw_value) == expected


def test_build_missing_snapshot_matches_session_missing_until() -> None:
    snapshot = subject.build_missing_snapshot(
        session_name="demo",
        until="session-missing",
        session_error="gone",
    )

    assert snapshot.session_exists is False
    assert snapshot.total_targets == 1
    assert snapshot.matched_targets == 1
    assert snapshot.criterion_satisfied is True
    assert snapshot.session_error == "gone"


def test_evaluate_trace_snapshot_counts_categories_and_matches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_classify_pane_status(
        pane: dict[str, str],
        *,
        pane_process_label_finder: object,
    ) -> tuple[str, str]:
        _ = pane_process_label_finder
        match pane["pane_index"]:
            case "0":
                return ("bash", "idle shell")
            case "1":
                return ("python", "running: pytest")
            case "2":
                return ("bash", "exited (code 7)")
            case _:
                return ("bash", "waiting")

    monkeypatch.setattr(subject, "classify_pane_status", fake_classify_pane_status)

    snapshot = subject.evaluate_trace_snapshot(
        session_name="demo",
        windows=[{"window_index": "1", "window_name": "main"}],
        panes_by_window={
            "1": [
                {
                    "pane_index": "0",
                    "pane_cwd": "",
                    "pane_active": "1",
                    "pane_dead_status": "",
                },
                {
                    "pane_index": "1",
                    "pane_cwd": "/work",
                    "pane_active": "",
                    "pane_dead_status": "",
                },
                {
                    "pane_index": "2",
                    "pane_cwd": "/logs",
                    "pane_active": "",
                    "pane_dead_status": "7",
                },
                {
                    "pane_index": "3",
                    "pane_cwd": "/tmp",
                    "pane_active": "",
                    "pane_dead_status": "oops",
                },
            ]
        },
        until="all-exited",
        expected_exit_code=None,
        pane_warning="warn",
    )

    assert snapshot.total_windows == 1
    assert snapshot.total_targets == 4
    assert snapshot.matched_targets == 1
    assert snapshot.criterion_satisfied is False
    assert snapshot.idle_shell_panes == 1
    assert snapshot.running_panes == 1
    assert snapshot.exited_panes == 1
    assert snapshot.unknown_panes == 1
    assert snapshot.panes[0].cwd == "—"
    assert snapshot.panes[0].is_active is True
    assert snapshot.panes[2].exit_code == 7
    assert snapshot.panes[2].matched is True
    assert snapshot.panes[3].matched is False
    assert snapshot.pane_warning == "warn"


def test_load_trace_snapshot_returns_missing_snapshot_when_session_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        subject,
        "check_tmux_session_status",
        lambda *, session_name: {"session_exists": False, "error": f"{session_name} missing"},
    )

    snapshot = subject.load_trace_snapshot("demo", "idle-shell", None)

    assert snapshot.session_exists is False
    assert snapshot.session_error == "demo missing"
    assert snapshot.criterion_satisfied is False


def test_load_trace_snapshot_uses_collected_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        subject,
        "check_tmux_session_status",
        lambda *, session_name: {"session_exists": True, "name": session_name},
    )
    monkeypatch.setattr(
        subject,
        "collect_session_snapshot",
        lambda *, session_name, run_command_fn: (
            [{"window_index": "1", "window_name": session_name}],
            {
                "1": [
                    {
                        "pane_index": "0",
                        "pane_cwd": "/repo",
                        "pane_active": "1",
                        "pane_dead_status": "",
                    }
                ]
            },
            "minor warning",
        ),
    )

    def fake_classify_pane_status(
        pane: dict[str, str],
        *,
        pane_process_label_finder: object,
    ) -> tuple[str, str]:
        _ = pane, pane_process_label_finder
        return ("bash", "idle shell")

    monkeypatch.setattr(subject, "classify_pane_status", fake_classify_pane_status)

    snapshot = subject.load_trace_snapshot("demo", "idle-shell", cast(int | None, None))

    assert snapshot.session_exists is True
    assert snapshot.session_name == "demo"
    assert snapshot.total_targets == 1
    assert snapshot.matched_targets == 1
    assert snapshot.criterion_satisfied is True
    assert snapshot.pane_warning == "minor warning"
