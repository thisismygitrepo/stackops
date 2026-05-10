import platform

import pytest

from stackops.scripts.python import terminal


def test_resolve_session_backend_accepts_tmux_on_windows(
    monkeypatch,
) -> None:
    monkeypatch.setattr(platform, "system", lambda: "Windows")

    assert terminal._resolve_session_backend("tmux") == "tmux"


def test_resolve_session_backend_auto_picks_tmux_on_windows(
    monkeypatch,
) -> None:
    monkeypatch.setattr(platform, "system", lambda: "Windows")

    assert terminal._resolve_session_backend("auto") == "tmux"


def test_attach_to_session_tmux_hands_off_attach_script_to_shell(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, str | bool] = {}

    def fake_choose_session(
        backend: str,
        name: str | None,
        new_session: bool,
        kill_all: bool,
        window: bool,
    ) -> tuple[str, str | None]:
        _ = backend, name, new_session, kill_all, window
        return ("run_script", "tmux attach -t demo")

    def fake_exit_then_run_shell_script(script: str, strict: bool = False) -> None:
        captured["script"] = script
        captured["strict"] = strict

    monkeypatch.setattr(terminal, "_resolve_session_backend", lambda backend: "tmux")
    monkeypatch.setattr(
        "stackops.scripts.python.helpers.helpers_sessions.attach_impl.choose_session",
        fake_choose_session,
    )
    monkeypatch.setattr(
        "stackops.utils.code.exit_then_run_shell_script",
        fake_exit_then_run_shell_script,
    )

    terminal.attach_to_session(name="demo")

    assert captured == {"script": "tmux attach -t demo", "strict": True}


def test_attach_to_session_tmux_hands_off_new_session_script_to_shell(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, str | bool] = {}

    def fake_choose_session(
        backend: str,
        name: str | None,
        new_session: bool,
        kill_all: bool,
        window: bool,
    ) -> tuple[str, str | None]:
        _ = backend, name, new_session, kill_all, window
        return ("tmux_new_session", "kill_all")

    def fake_exit_then_run_shell_script(script: str, strict: bool = False) -> None:
        captured["script"] = script
        captured["strict"] = strict

    monkeypatch.setattr(terminal, "_resolve_session_backend", lambda backend: "tmux")
    monkeypatch.setattr(
        "stackops.scripts.python.helpers.helpers_sessions.attach_impl.choose_session",
        fake_choose_session,
    )
    monkeypatch.setattr(
        "stackops.utils.code.exit_then_run_shell_script",
        fake_exit_then_run_shell_script,
    )

    terminal.attach_to_session(name=None, new_session=True, kill_all=True)

    assert captured == {
        "script": "tmux kill-server\nif [ -n \"${TMUX:-}\" ]; then new_session_name=$(tmux new-session -d -P -F '#{session_name}') && tmux switch-client -t \"$new_session_name\"; else tmux new-session; fi",
        "strict": True,
    }