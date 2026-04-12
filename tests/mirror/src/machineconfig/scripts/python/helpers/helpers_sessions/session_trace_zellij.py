from __future__ import annotations

import pytest

import machineconfig.scripts.python.helpers.helpers_sessions.session_trace_zellij as subject


def test_load_trace_snapshot_is_not_implemented() -> None:
    with pytest.raises(NotImplementedError, match="tmux backend only"):
        subject.load_trace_snapshot("demo", "idle-shell", None)
