from unittest.mock import patch

from typer.testing import CliRunner

from machineconfig.scripts.python import sessions
from machineconfig.scripts.python.helpers.helpers_sessions.sessions_trace import (
    evaluate_trace_snapshot,
)


runner = CliRunner()


def test_trace_command_dispatches_to_impl() -> None:
    with patch(
        "machineconfig.scripts.python.helpers.helpers_sessions.sessions_trace.trace_session"
    ) as trace_session:
        result = runner.invoke(
            sessions.get_app(),
            [
                "trace",
                "build-session",
                "--every",
                "7",
                "--until",
                "exit-code",
                "--exit-code",
                "0",
            ],
        )

    assert result.exit_code == 0
    trace_session.assert_called_once_with(
        session_name="build-session",
        until="exit-code",
        every_seconds=7.0,
        exit_code=0,
    )


def test_trace_command_requires_exit_code_for_exit_code_criterion() -> None:
    result = runner.invoke(
        sessions.get_app(),
        ["trace", "build-session", "--until", "exit-code"],
    )

    assert result.exit_code != 0
    assert "--exit-code" in result.output


def test_evaluate_trace_snapshot_counts_idle_shell_progress() -> None:
    snapshot = evaluate_trace_snapshot(
        session_name="build-session",
        windows=[
            {
                "window_index": "1",
                "window_name": "editor",
                "window_panes": "1",
                "window_active": "active",
            },
            {
                "window_index": "2",
                "window_name": "runner",
                "window_panes": "1",
                "window_active": "",
            },
        ],
        panes_by_window={
            "1": [
                {
                    "pane_index": "0",
                    "pane_cwd": "/repo",
                    "pane_command": "bash",
                    "pane_active": "active",
                    "pane_dead": "",
                    "pane_dead_status": "",
                    "pane_pid": "",
                }
            ],
            "2": [
                {
                    "pane_index": "0",
                    "pane_cwd": "/repo",
                    "pane_command": "python",
                    "pane_active": "",
                    "pane_dead": "",
                    "pane_dead_status": "",
                    "pane_pid": "",
                }
            ],
        },
        until="idle-shell",
        expected_exit_code=None,
        pane_warning=None,
    )

    assert snapshot.session_exists is True
    assert snapshot.total_targets == 2
    assert snapshot.matched_targets == 1
    assert snapshot.idle_shell_panes == 1
    assert snapshot.running_panes == 1
    assert snapshot.criterion_satisfied is False


def test_evaluate_trace_snapshot_requires_matching_exit_code() -> None:
    snapshot = evaluate_trace_snapshot(
        session_name="build-session",
        windows=[
            {
                "window_index": "1",
                "window_name": "runner",
                "window_panes": "2",
                "window_active": "active",
            }
        ],
        panes_by_window={
            "1": [
                {
                    "pane_index": "0",
                    "pane_cwd": "/repo",
                    "pane_command": "bash",
                    "pane_active": "active",
                    "pane_dead": "dead",
                    "pane_dead_status": "0",
                    "pane_pid": "",
                },
                {
                    "pane_index": "1",
                    "pane_cwd": "/repo",
                    "pane_command": "bash",
                    "pane_active": "",
                    "pane_dead": "dead",
                    "pane_dead_status": "1",
                    "pane_pid": "",
                },
            ]
        },
        until="exit-code",
        expected_exit_code=0,
        pane_warning=None,
    )

    assert snapshot.exited_panes == 2
    assert snapshot.matched_targets == 1
    assert snapshot.criterion_satisfied is False
