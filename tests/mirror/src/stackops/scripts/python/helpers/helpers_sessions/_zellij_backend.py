from subprocess import CompletedProcess

import pytest

from stackops.scripts.python.helpers.helpers_sessions import _zellij_backend
from stackops.scripts.python.helpers.helpers_sessions._zellij_backend_options import (
    new_session_script,
)


def test_choose_session_new_session_returns_handoff_script() -> None:
    action, script = _zellij_backend.choose_session(
        name=None,
        new_session=True,
        kill_all=True,
        window=False,
    )

    assert action == "handoff_script"
    assert script == new_session_script(
        standard_layout=_zellij_backend.STANDARD,
        quote_fn=_zellij_backend.quote,
        kill_all=True,
    )


def test_choose_session_without_existing_sessions_returns_handoff_script(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run_command(args: list[str], timeout: float = 5.0) -> CompletedProcess[str]:
        _ = timeout
        return CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(_zellij_backend, "run_command", fake_run_command)

    action, script = _zellij_backend.choose_session(
        name=None,
        new_session=False,
        kill_all=False,
        window=False,
    )

    assert action == "handoff_script"
    assert script == new_session_script(
        standard_layout=_zellij_backend.STANDARD,
        quote_fn=_zellij_backend.quote,
        kill_all=False,
    )