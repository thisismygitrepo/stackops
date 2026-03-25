from machineconfig.scripts.python.helpers.helpers_sessions.session_trace_tmux import (
    TraceSnapshot,
    TraceUntil,
)


def load_trace_snapshot(
    session_name: str,
    until: TraceUntil,
    expected_exit_code: int | None,
) -> TraceSnapshot:
    _ = session_name, until, expected_exit_code
    raise NotImplementedError(
        "Zellij trace is not implemented yet. `sessions trace` currently uses the tmux backend only."
    )
