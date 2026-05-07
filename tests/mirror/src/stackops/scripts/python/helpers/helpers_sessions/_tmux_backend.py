from subprocess import CompletedProcess

import pytest

from stackops.scripts.python.helpers.helpers_sessions import _tmux_backend
from stackops.scripts.python.helpers.helpers_sessions._tmux_backend_options import new_session_script


def test_choose_session_new_session_uses_nested_safe_script() -> None:
    action, script = _tmux_backend.choose_session(
        name=None,
        new_session=True,
        kill_all=False,
        window=False,
    )

    assert action == "run_script"
    assert script == new_session_script(kill_all=False)
    assert script is not None
    assert """tmux new-session -d -P -F '#{session_name}'""" in script
    assert 'tmux switch-client -t "$new_session_name"' in script


def test_choose_session_without_existing_sessions_uses_nested_safe_script(
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

    assert action == "run_script"
    assert script == new_session_script(kill_all=False)
