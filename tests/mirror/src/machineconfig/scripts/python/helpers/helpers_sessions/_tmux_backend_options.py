from __future__ import annotations

from collections.abc import Callable
from subprocess import CompletedProcess

import pytest

from machineconfig.scripts.python.helpers.helpers_sessions import _tmux_backend_options as tmux_options


def _quote(value: str) -> str:
    return f"<{value}>"


def test_attach_script_from_name_parses_window_targets(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_attach(session_name: str) -> str:
        return f"ATTACH {session_name}"

    monkeypatch.setattr(tmux_options, "build_tmux_attach_or_switch_command", fake_attach)

    pane_script = tmux_options.attach_script_from_name(name="work:2.1", quote_fn=_quote)
    window_script = tmux_options.attach_script_from_name(name="work:2", quote_fn=_quote)
    session_script = tmux_options.attach_script_from_name(name="work", quote_fn=_quote)

    assert pane_script == "tmux select-window -t <work:2>\ntmux select-pane -t <work:2.1>\nATTACH work"
    assert window_script == "tmux select-window -t <work:2>\nATTACH work"
    assert session_script == "ATTACH work"


def test_kill_script_for_target_handles_session_window_and_pane() -> None:
    assert tmux_options.kill_script_for_target(session_name="work", quote_fn=_quote) == "tmux kill-session -t <work>"
    assert tmux_options.kill_script_for_target(session_name="work", quote_fn=_quote, window_target="2") == "tmux kill-window -t <work:2>"
    assert (
        tmux_options.kill_script_for_target(session_name="work", quote_fn=_quote, window_target="2", pane_index="1") == "tmux kill-pane -t <work:2.1>"
    )


def test_build_window_target_options_builds_labels_previews_and_skips_missing_sessions(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_attach(session_name: str) -> str:
        return f"ATTACH {session_name}"

    def fake_collect_snapshot(
        session_name: str, run_command_fn: Callable[[list[str]], CompletedProcess[str]]
    ) -> tuple[list[dict[str, str]] | None, dict[str, list[dict[str, str]]], str | None]:
        del run_command_fn
        if session_name == "beta":
            return (None, {}, "unreachable")
        return (
            [{"window_index": "1", "window_name": "editor", "window_panes": "1", "window_active": "active"}],
            {
                "1": [
                    {
                        "pane_index": "0",
                        "pane_cwd": "/tmp/project",
                        "pane_command": "bash",
                        "pane_active": "active",
                        "pane_dead": "",
                        "pane_dead_status": "",
                        "pane_pid": "100",
                    }
                ]
            },
            None,
        )

    def fake_build_window_preview(
        session_name: str,
        window: dict[str, str],
        panes: list[dict[str, str]],
        pane_warning: str | None,
        classify_pane_status_fn: Callable[[dict[str, str]], tuple[str, str]],
    ) -> str:
        del panes, pane_warning, classify_pane_status_fn
        return f"WINDOW {session_name}:{window['window_index']}"

    def fake_build_pane_preview(
        session_name: str, window: dict[str, str], pane: dict[str, str], classify_pane_status_fn: Callable[[dict[str, str]], tuple[str, str]]
    ) -> str:
        del classify_pane_status_fn
        return f"PANE {session_name}:{window['window_index']}.{pane['pane_index']}"

    def fake_classify(_: dict[str, str]) -> tuple[str, str]:
        return ("shell", "idle shell")

    def fake_run_command(args: list[str]) -> CompletedProcess[str]:
        raise AssertionError(f"unexpected command: {args}")

    monkeypatch.setattr(tmux_options, "build_tmux_attach_or_switch_command", fake_attach)
    monkeypatch.setattr(tmux_options, "collect_session_snapshot", fake_collect_snapshot)
    monkeypatch.setattr(tmux_options, "build_window_preview", fake_build_window_preview)
    monkeypatch.setattr(tmux_options, "build_pane_preview", fake_build_pane_preview)

    scripts, previews = tmux_options.build_window_target_options(
        sessions=["alpha", "beta"], run_command_fn=fake_run_command, classify_pane_status_fn=fake_classify, quote_fn=_quote
    )

    assert scripts == {
        "[alpha] 1:editor *": "tmux select-window -t <alpha:1>\nATTACH alpha",
        "[alpha] 1:editor.0 shell *": "tmux select-window -t <alpha:1>\ntmux select-pane -t <alpha:1.0>\nATTACH alpha",
    }
    assert previews == {"[alpha] 1:editor *": "WINDOW alpha:1", "[alpha] 1:editor.0 shell *": "PANE alpha:1.0"}
