from stackops.scripts.python.helpers.helpers_sessions import session_trace_tmux


def test_evaluate_trace_snapshot_preserves_stable_tmux_kill_targets() -> None:
    snapshot = session_trace_tmux.evaluate_trace_snapshot(
        session_name="build",
        windows=[
            {
                "window_index": "1",
                "window_name": "main",
                "window_id": "@10",
            }
        ],
        panes_by_window={
            "1": [
                {
                    "pane_index": "0",
                    "pane_cwd": "/work",
                    "pane_command": "python",
                    "pane_active": "active",
                    "pane_dead": "dead",
                    "pane_dead_status": "0",
                    "pane_pid": "100",
                    "pane_id": "%10",
                }
            ]
        },
        until="all-exited",
        expected_exit_code=None,
        pane_warning=None,
    )

    assert snapshot.session_target == "build"
    assert snapshot.panes[0].window_target == "@10"
    assert snapshot.panes[0].pane_target == "%10"
    assert snapshot.criterion_satisfied is True
