import platform

import pytest
import typer

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
    ) -> tuple[str, str]:
        _ = backend, name, new_session, kill_all, window
        return ("handoff_script", "tmux attach -t demo")

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
    ) -> tuple[str, str]:
        _ = backend, name, new_session, kill_all, window
        return ("handoff_script", "tmux kill-server\nif [ -n \"${TMUX:-}\" ]; then new_session_name=$(tmux new-session -d -P -F '#{session_name}') && tmux switch-client -t \"$new_session_name\"; else tmux new-session; fi")

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


@pytest.mark.parametrize(
    ("kwargs", "expected_error"),
    [
        ({"new_session": True}, "Error: NAME cannot be used together with --new-session."),
        ({"kill_all": True}, "Error: NAME cannot be used together with --kill-all."),
        ({"window": True}, "Error: NAME cannot be used together with --window."),
    ],
)
def test_attach_to_session_rejects_name_with_conflicting_options(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    kwargs: dict[str, bool],
    expected_error: str,
) -> None:
    def fail_to_resolve_backend(_backend: str) -> str:
        raise AssertionError("attach_to_session should validate conflicting arguments before resolving the backend")

    monkeypatch.setattr(terminal, "_resolve_session_backend", fail_to_resolve_backend)

    with pytest.raises(typer.Exit) as exc_info:
        terminal.attach_to_session(name="demo", **kwargs)

    captured = capsys.readouterr()
    assert exc_info.value.exit_code == 1
    assert expected_error in captured.err


def test_attach_to_session_exits_nonzero_when_helper_reports_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_choose_session(
        backend: str,
        name: str | None,
        new_session: bool,
        kill_all: bool,
        window: bool,
    ) -> tuple[str, str]:
        _ = backend, name, new_session, kill_all, window
        return ("error", "No tmux session selected.")

    monkeypatch.setattr(terminal, "_resolve_session_backend", lambda backend: "tmux")
    monkeypatch.setattr(
        "stackops.scripts.python.helpers.helpers_sessions.attach_impl.choose_session",
        fake_choose_session,
    )

    with pytest.raises(typer.Exit) as exc_info:
        terminal.attach_to_session(name=None)

    assert exc_info.value.exit_code == 1


def test_attach_to_session_rejects_non_handoff_actions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_choose_session(
        backend: str,
        name: str | None,
        new_session: bool,
        kill_all: bool,
        window: bool,
    ) -> tuple[str, str]:
        _ = backend, name, new_session, kill_all, window
        return ("unexpected", "echo no")

    def fake_exit_then_run_shell_script(script: str, strict: bool = False) -> None:
        _ = script, strict
        raise AssertionError("attach_to_session should not hand off unknown actions")

    monkeypatch.setattr(terminal, "_resolve_session_backend", lambda backend: "tmux")
    monkeypatch.setattr(
        "stackops.scripts.python.helpers.helpers_sessions.attach_impl.choose_session",
        fake_choose_session,
    )
    monkeypatch.setattr(
        "stackops.utils.code.exit_then_run_shell_script",
        fake_exit_then_run_shell_script,
    )

    with pytest.raises(typer.Exit) as exc_info:
        terminal.attach_to_session(name="demo")

    assert exc_info.value.exit_code == 1
