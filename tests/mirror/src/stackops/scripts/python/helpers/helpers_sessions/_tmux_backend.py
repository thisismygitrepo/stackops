

from subprocess import CompletedProcess

import pytest

from stackops.scripts.python.helpers.helpers_sessions import _tmux_backend as tmux_backend
from stackops.scripts.python.helpers.helpers_sessions.attach_impl import KILL_ALL_AND_NEW_LABEL, NEW_SESSION_LABEL


def _completed_process(stdout: str, returncode: int, stderr: str) -> CompletedProcess[str]:
    return CompletedProcess(args=["tmux"], returncode=returncode, stdout=stdout, stderr=stderr)


def test_choose_session_sorts_options_and_runs_selected_session(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_options: dict[str, str] = {}

    def fake_run_command(args: list[str]) -> CompletedProcess[str]:
        assert args == ["tmux", "list-sessions", "-F", "#S"]
        return _completed_process(stdout="beta\nalpha\n", returncode=0, stderr="")

    def fake_build_preview(session_name: str) -> str:
        return f"preview:{session_name}"

    def fake_choose(msg: str, options_to_preview_mapping: dict[str, str], multi: bool = False) -> str | None:
        assert msg == "Choose a tmux session to attach to:"
        assert not multi
        captured_options.update(options_to_preview_mapping)
        return "alpha"

    def fake_attach(session_name: str) -> str:
        return f"ATTACH {session_name}"

    monkeypatch.setattr(tmux_backend, "run_command", fake_run_command)
    monkeypatch.setattr(tmux_backend, "_build_preview", fake_build_preview)
    monkeypatch.setattr(tmux_backend, "interactive_choose_with_preview", fake_choose)
    monkeypatch.setattr(tmux_backend, "build_tmux_attach_or_switch_command", fake_attach)

    result = tmux_backend.choose_session(name=None, new_session=False, kill_all=False)

    assert result == ("run_script", "ATTACH alpha")
    assert list(captured_options) == ["alpha", "beta", NEW_SESSION_LABEL, KILL_ALL_AND_NEW_LABEL]


def test_choose_session_window_returns_error_for_unknown_target(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run_command(args: list[str]) -> CompletedProcess[str]:
        assert args == ["tmux", "list-sessions", "-F", "#S"]
        return _completed_process(stdout="main\n", returncode=0, stderr="")

    def fake_build_window_target_options(
        sessions: list[str], run_command_fn: object, classify_pane_status_fn: object, quote_fn: object
    ) -> tuple[dict[str, str], dict[str, str]]:
        del run_command_fn, classify_pane_status_fn, quote_fn
        assert sessions == ["main"]
        return ({"[main] 1:code": "ATTACH-CODE", "[main] 2:logs": "ATTACH-LOGS"}, {"[main] 1:code": "preview-code", "[main] 2:logs": "preview-logs"})

    def fake_choose(msg: str, options_to_preview_mapping: dict[str, str], multi: bool = False) -> str | None:
        assert msg == "Choose a tmux window or pane to attach to:"
        assert not multi
        assert "[main] 1:code" in options_to_preview_mapping
        return "missing"

    monkeypatch.setattr(tmux_backend, "run_command", fake_run_command)
    monkeypatch.setattr(tmux_backend, "build_window_target_options", fake_build_window_target_options)
    monkeypatch.setattr(tmux_backend, "interactive_choose_with_preview", fake_choose)

    result = tmux_backend.choose_session(name=None, new_session=False, kill_all=False, window=True)

    assert result == ("error", "Unknown tmux target selected: missing")


def test_choose_kill_target_window_deduplicates_selected_scripts(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run_command(args: list[str]) -> CompletedProcess[str]:
        assert args == ["tmux", "list-sessions", "-F", "#S"]
        return _completed_process(stdout="main\naux\n", returncode=0, stderr="")

    def fake_kill_script_for_target(session_name: str, quote_fn: object, window_target: str | None = None, pane_index: str | None = None) -> str:
        del quote_fn, window_target, pane_index
        return f"KILL {session_name}"

    def fake_build_kill_target_options(
        sessions: list[str], run_command_fn: object, classify_pane_status_fn: object, quote_fn: object
    ) -> tuple[dict[str, str], dict[str, str]]:
        del run_command_fn, classify_pane_status_fn, quote_fn
        session_name = sessions[0]
        return ({f"[{session_name}] 1:work.0 shell": f"PANE {session_name}"}, {f"[{session_name}] 1:work.0 shell": f"preview:{session_name}"})

    def fake_build_preview(session_name: str) -> str:
        return f"preview:{session_name}"

    def fake_choose(msg: str, options_to_preview_mapping: dict[str, str], multi: bool = False) -> list[str]:
        assert msg == "Choose a tmux session, window, or pane to kill:"
        assert multi
        assert "[main] SESSION" in options_to_preview_mapping
        return ["[main] SESSION", "[main] 1:work.0 shell", "[main] 1:work.0 shell", "[aux] SESSION"]

    monkeypatch.setattr(tmux_backend, "run_command", fake_run_command)
    monkeypatch.setattr(tmux_backend, "kill_script_for_target", fake_kill_script_for_target)
    monkeypatch.setattr(tmux_backend, "build_kill_target_options", fake_build_kill_target_options)
    monkeypatch.setattr(tmux_backend, "_build_preview", fake_build_preview)
    monkeypatch.setattr(tmux_backend, "interactive_choose_with_preview", fake_choose)

    result = tmux_backend.choose_kill_target(name=None, kill_all=False, window=True)

    assert result == ("run_script", "KILL main\nPANE main\nKILL aux")
