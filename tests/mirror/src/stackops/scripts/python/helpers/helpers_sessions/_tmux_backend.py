from subprocess import CompletedProcess

import pytest

from stackops.scripts.python.helpers.helpers_sessions import _tmux_backend
from stackops.scripts.python.helpers.helpers_sessions._tmux_backend_options import (
    new_session_script,
)


def test_choose_session_new_session_returns_tmux_new_session_action() -> None:
    action, script = _tmux_backend.choose_session(
        name=None,
        new_session=True,
        kill_all=False,
        window=False,
    )

    assert action == "handoff_script"
    assert script == new_session_script(kill_all=False)


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

    assert action == "handoff_script"
    assert script == new_session_script(kill_all=False)


def test_choose_session_deduplicates_new_session_choices_when_kill_all_is_requested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_options: dict[str, str] = {}

    def fake_run_command(args: list[str], timeout: float = 5.0) -> CompletedProcess[str]:
        _ = timeout
        return CompletedProcess(args=args, returncode=0, stdout="demo\nother\n", stderr="")

    def fake_build_preview(session_name: str) -> str:
        return f"preview for {session_name}"

    def fake_choose_with_preview(
        msg: str,
        options_to_preview_mapping: dict[str, str],
        multi: bool = False,
    ) -> str | list[str] | None:
        _ = msg, multi
        captured_options.update(options_to_preview_mapping)
        return _tmux_backend.NEW_SESSION_LABEL

    monkeypatch.setattr(_tmux_backend, "run_command", fake_run_command)
    monkeypatch.setattr(_tmux_backend, "_build_preview", fake_build_preview)
    monkeypatch.setattr(_tmux_backend, "interactive_choose_with_preview", fake_choose_with_preview)

    action, script = _tmux_backend.choose_session(
        name=None,
        new_session=False,
        kill_all=True,
        window=False,
    )

    assert action == "handoff_script"
    assert script == new_session_script(kill_all=True)
    assert _tmux_backend.NEW_SESSION_LABEL in captured_options
    assert _tmux_backend.KILL_ALL_AND_NEW_LABEL not in captured_options
