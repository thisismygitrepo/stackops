from subprocess import CompletedProcess

import pytest

from stackops.scripts.python.helpers.helpers_sessions import _tmux_backend


def test_choose_session_new_session_returns_tmux_new_session_action() -> None:
    action, script = _tmux_backend.choose_session(
        name=None,
        new_session=True,
        kill_all=False,
        window=False,
    )

    assert action == "tmux_new_session"
    assert script == ""


def test_choose_session_without_existing_sessions_returns_tmux_new_session_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run_command(args: list[str], timeout: float = 5.0) -> CompletedProcess[str]:
        _ = timeout
        return CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(_tmux_backend, "run_command", fake_run_command)

    action, script = _tmux_backend.choose_session(
        name=None,
        new_session=False,
        kill_all=False,
        window=False,
    )

    assert action == "tmux_new_session"
    assert script == ""
