from __future__ import annotations

from subprocess import CompletedProcess

import pytest

from stackops.scripts.python.helpers.helpers_sessions import _zellij_backend as zellij_backend


def _completed_process(stdout: str, returncode: int, stderr: str) -> CompletedProcess[str]:
    return CompletedProcess(args=["zellij"], returncode=returncode, stdout=stdout, stderr=stderr)


def test_choose_session_rejects_current_session(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run_command(args: list[str]) -> CompletedProcess[str]:
        assert args == ["zellij", "list-sessions"]
        return _completed_process(stdout="proj [Created just-now] (current)\nother [Created earlier]\n", returncode=0, stderr="")

    monkeypatch.setattr(zellij_backend, "run_command", fake_run_command)

    result = zellij_backend.choose_session(name=None, new_session=False, kill_all=False)

    assert result == ("error", "Already in a Zellij session, avoiding nesting and exiting.")


def test_choose_session_window_uses_only_active_sessions(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_active_sessions: list[str] = []

    def fake_run_command(args: list[str]) -> CompletedProcess[str]:
        assert args == ["zellij", "list-sessions"]
        return _completed_process(stdout="live\narchive EXITED\n", returncode=0, stderr="")

    def fake_build_window_target_options(
        active_sessions: list[str], read_session_metadata_fn: object, get_live_tab_names_fn: object, quote_fn: object
    ) -> tuple[dict[str, str], dict[str, str]]:
        del read_session_metadata_fn, get_live_tab_names_fn, quote_fn
        captured_active_sessions.extend(active_sessions)
        return (
            {"[live] 1:code": "ATTACH CODE", "[live] 1:code / Pane #1": "ATTACH PANE"},
            {"[live] 1:code": "preview-tab", "[live] 1:code / Pane #1": "preview-pane"},
        )

    def fake_choose(msg: str, options_to_preview_mapping: dict[str, str], multi: bool = False) -> str | None:
        assert msg == "Choose a Zellij tab or pane to attach to:"
        assert not multi
        assert "[live] 1:code / Pane #1" in options_to_preview_mapping
        return "[live] 1:code / Pane #1"

    monkeypatch.setattr(zellij_backend, "run_command", fake_run_command)
    monkeypatch.setattr(zellij_backend, "build_window_target_options", fake_build_window_target_options)
    monkeypatch.setattr(zellij_backend, "interactive_choose_with_preview", fake_choose)

    result = zellij_backend.choose_session(name=None, new_session=False, kill_all=False, window=True)

    assert captured_active_sessions == ["live"]
    assert result == ("run_script", "ATTACH PANE")


def test_get_session_tabs_ignores_exited_sessions(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run_command(args: list[str]) -> CompletedProcess[str]:
        assert args == ["zellij", "list-sessions"]
        return _completed_process(stdout="one\nold EXITED\ntwo\n", returncode=0, stderr="")

    def fake_get_live_tab_names(session_name: str) -> list[str]:
        return {"one": ["code", "logs"], "two": ["shell"]}[session_name]

    monkeypatch.setattr(zellij_backend, "run_command", fake_run_command)
    monkeypatch.setattr(zellij_backend, "_get_live_tab_names", fake_get_live_tab_names)

    tabs = zellij_backend.get_session_tabs()

    assert tabs == [("one", "code"), ("one", "logs"), ("two", "shell")]


def test_choose_kill_target_window_marks_session_state_and_deduplicates(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run_command(args: list[str]) -> CompletedProcess[str]:
        assert args == ["zellij", "list-sessions"]
        return _completed_process(stdout="live\nold\n", returncode=0, stderr="")

    def fake_session_name(raw_line: str) -> str:
        return raw_line

    def fake_session_is_current(raw_line: str) -> bool:
        return raw_line == "live"

    def fake_session_is_exited(raw_line: str) -> bool:
        return raw_line == "old"

    def fake_kill_script_for_target(
        session_name: str, quote_fn: object, tab_name: str | None = None, pane_focus_commands: list[str] | None = None, kill_pane: bool = False
    ) -> str:
        del quote_fn, tab_name, pane_focus_commands, kill_pane
        return f"KILL {session_name}"

    def fake_build_preview(raw_line: str) -> str:
        return f"preview:{raw_line}"

    def fake_build_kill_target_options(
        active_sessions: list[str], read_session_metadata_fn: object, get_live_tab_names_fn: object, quote_fn: object
    ) -> tuple[dict[str, str], dict[str, str]]:
        del read_session_metadata_fn, get_live_tab_names_fn, quote_fn
        assert active_sessions == ["live"]
        return ({"[live] 1:code": "TAB live"}, {"[live] 1:code": "preview-tab"})

    def fake_choose(msg: str, options_to_preview_mapping: dict[str, str], multi: bool = False) -> list[str]:
        assert msg == "Choose a Zellij session, tab, or pane to kill:"
        assert multi
        assert "[live] SESSION (current)" in options_to_preview_mapping
        assert "[old] SESSION (exited)" in options_to_preview_mapping
        return ["[live] SESSION (current)", "[live] 1:code", "[live] 1:code", "[old] SESSION (exited)"]

    monkeypatch.setattr(zellij_backend, "run_command", fake_run_command)
    monkeypatch.setattr(zellij_backend, "_session_name", fake_session_name)
    monkeypatch.setattr(zellij_backend, "_session_is_current", fake_session_is_current)
    monkeypatch.setattr(zellij_backend, "_session_is_exited", fake_session_is_exited)
    monkeypatch.setattr(zellij_backend, "kill_script_for_target", fake_kill_script_for_target)
    monkeypatch.setattr(zellij_backend, "_build_preview", fake_build_preview)
    monkeypatch.setattr(zellij_backend, "build_kill_target_options", fake_build_kill_target_options)
    monkeypatch.setattr(zellij_backend, "interactive_choose_with_preview", fake_choose)

    result = zellij_backend.choose_kill_target(name=None, kill_all=False, window=True)

    assert result == ("run_script", "KILL live\nTAB live\nKILL old")
