from subprocess import CompletedProcess

import pytest

from stackops.cluster.sessions_managers.tmux.tmux_utils import tmux_execution


def test_run_tmux_commands_splits_quoted_arguments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run(
        args: list[str],
        capture_output: bool,
        text: bool,
        timeout: float | None,
        check: bool,
    ) -> CompletedProcess[str]:
        _ = capture_output, text, timeout, check
        calls.append(args)
        return CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(tmux_execution.subprocess, "run", fake_run)

    tmux_execution.run_tmux_commands(
        commands=["tmux send-keys -t demo:Agent0 'echo hello world' C-m"],
        timeout_seconds=5.0,
    )

    assert calls == [["tmux", "send-keys", "-t", "demo:Agent0", "echo hello world", "C-m"]]


def test_run_tmux_script_chooses_attach_outside_tmux(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[list[str], float | None]] = []

    def fake_run(
        args: list[str],
        capture_output: bool,
        text: bool,
        timeout: float | None,
        check: bool,
    ) -> CompletedProcess[str]:
        _ = capture_output, text, check
        calls.append((args, timeout))
        return CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(tmux_execution.subprocess, "run", fake_run)
    monkeypatch.delenv("TMUX", raising=False)

    tmux_execution.run_tmux_script(
        script=tmux_execution.build_tmux_attach_or_switch_command(session_name="demo"),
        timeout_seconds=5.0,
    )

    assert calls == [(["tmux", "attach", "-t", "demo"], None)]


def test_run_tmux_script_switches_client_inside_tmux(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[list[str], float | None]] = []

    def fake_run(
        args: list[str],
        capture_output: bool,
        text: bool,
        timeout: float | None,
        check: bool,
    ) -> CompletedProcess[str]:
        _ = capture_output, text, check
        calls.append((args, timeout))
        return CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(tmux_execution.subprocess, "run", fake_run)
    monkeypatch.setenv("TMUX", "inside")

    tmux_execution.run_tmux_script(
        script=tmux_execution.build_tmux_attach_or_switch_command(session_name="demo"),
        timeout_seconds=5.0,
    )

    assert calls == [(["tmux", "switch-client", "-t", "demo"], 5.0)]


def test_start_tmux_new_session_outside_tmux_has_no_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[list[str], float | None]] = []

    def fake_run(
        args: list[str],
        timeout: float | None,
        check: bool,
    ) -> CompletedProcess[str]:
        _ = check
        calls.append((args, timeout))
        return CompletedProcess(args=args, returncode=0)

    monkeypatch.setattr(tmux_execution.subprocess, "run", fake_run)
    monkeypatch.delenv("TMUX", raising=False)

    tmux_execution.start_tmux_new_session(
        kill_all=False,
        timeout_seconds=5.0,
    )

    assert calls == [(["tmux", "new-session"], None)]