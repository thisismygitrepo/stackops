from dataclasses import dataclass
import subprocess

import pytest

from stackops.scripts.python.helpers.helpers_sessions import _tmux_backend
from stackops.scripts.python.helpers.helpers_sessions.attach_impl import (
    KILL_ALL_AND_NEW_LABEL,
    NEW_SESSION_LABEL,
)


@dataclass
class SingleChoiceCapture:
    message: str | None
    options: tuple[str, ...] | None


def test_single_tmux_session_still_shows_attach_picker(monkeypatch: pytest.MonkeyPatch) -> None:
    capture = SingleChoiceCapture(message=None, options=None)

    def fake_run_command(args: list[str]) -> subprocess.CompletedProcess[str]:
        assert args == ["tmux", "list-sessions", "-F", "#S"]
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="0\n", stderr="")

    def fake_build_preview(session_name: str) -> str:
        assert session_name == "0"
        return "session zero preview"

    def fake_interactive_choose_with_preview(
        *,
        msg: str,
        options_to_preview_mapping: dict[str, str],
    ) -> str | None:
        capture.message = msg
        capture.options = tuple(options_to_preview_mapping)
        return NEW_SESSION_LABEL

    monkeypatch.setattr(_tmux_backend, "run_command", fake_run_command)
    monkeypatch.setattr(_tmux_backend, "_build_preview", fake_build_preview)
    monkeypatch.setattr(
        _tmux_backend,
        "interactive_choose_with_preview",
        fake_interactive_choose_with_preview,
    )

    action, payload = _tmux_backend.choose_session(
        name=None,
        new_session=False,
        kill_all=False,
        window=False,
    )

    assert action == "run_script"
    assert payload == "tmux new-session"
    assert capture.message == "Choose a tmux session to attach to:"
    assert capture.options == ("0", NEW_SESSION_LABEL, KILL_ALL_AND_NEW_LABEL)
