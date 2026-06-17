import subprocess
from typing import Any

from stackops.cluster.sessions_managers.tmux.tmux_utils import tmux_execution


def test_build_next_numeric_tmux_session_name_reuses_lowest_free_number() -> None:
    assert tmux_execution.build_next_numeric_tmux_session_name({"3", "34", "alpha"}) == "1"
    assert tmux_execution.build_next_numeric_tmux_session_name({"1", "2", "34"}) == "3"


def test_new_session_handoff_script_names_sessions_explicitly() -> None:
    script = tmux_execution.build_tmux_new_session_command()

    assert "tmux list-sessions" in script
    assert 'tmux new-session -d -s "$new_session_name"' in script
    assert 'tmux new-session -s "$new_session_name"' in script
    assert "-P -F" not in script


def test_start_tmux_new_session_inside_tmux_reuses_lowest_free_number(
    monkeypatch: Any,
) -> None:
    calls: list[list[str]] = []

    def fake_run(args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        if args == ["tmux", "list-sessions", "-F", "#{session_name}"]:
            return subprocess.CompletedProcess(args, 0, "2\n34\nalpha\n", "")
        if args == ["tmux", "new-session", "-d", "-s", "1"]:
            return subprocess.CompletedProcess(args, 0, "", "")
        if args == ["tmux", "switch-client", "-t", "1"]:
            return subprocess.CompletedProcess(args, 0, "", "")
        return subprocess.CompletedProcess(args, 1, "", f"unexpected command: {args}")

    monkeypatch.setenv("TMUX", "/tmp/tmux-session")
    monkeypatch.setattr(tmux_execution.subprocess, "run", fake_run)

    tmux_execution.start_tmux_new_session(kill_all=False, timeout_seconds=5.0)

    assert calls == [
        ["tmux", "list-sessions", "-F", "#{session_name}"],
        ["tmux", "new-session", "-d", "-s", "1"],
        ["tmux", "switch-client", "-t", "1"],
    ]


def test_run_tmux_script_dispatches_multiline_new_session_script(
    monkeypatch: Any,
) -> None:
    observed: list[tuple[bool, float | None]] = []

    def fake_start_tmux_new_session(
        kill_all: bool,
        timeout_seconds: float | None,
    ) -> None:
        observed.append((kill_all, timeout_seconds))

    monkeypatch.setattr(tmux_execution, "start_tmux_new_session", fake_start_tmux_new_session)

    result = tmux_execution.run_tmux_script(
        script=f"tmux kill-server\n{tmux_execution.build_tmux_new_session_command()}",
        timeout_seconds=7.0,
    )

    assert result == []
    assert observed == [(True, 7.0)]
