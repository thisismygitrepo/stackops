import subprocess
from typing import Callable

import pytest

from stackops.scripts.python.helpers.helpers_sessions import _tmux_backend
from stackops.scripts.python.helpers.helpers_sessions._tmux_backend_options import (
    build_idle_kill_script_for_sessions,
)
from stackops.scripts.python.helpers.helpers_sessions.kill_impl import KilledTarget


def _single_quote(value: str) -> str:
    return f"'{value}'"


def _classify_by_pane_command(pane: dict[str, str]) -> tuple[str, str]:
    pane_command = pane["pane_command"]
    if pane_command == "bash":
        return (pane_command, "idle shell")
    return (pane_command, f"running: `{pane_command}`")


def test_idle_kill_script_kills_idle_windows_and_mixed_idle_panes() -> None:
    def fake_run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
        if "list-windows" in command:
            return subprocess.CompletedProcess(
                command,
                0,
                "0\tmain\t2\tactive\t@10\n1\twork\t2\t\t@11\n",
                "",
            )
        if "list-panes" in command:
            return subprocess.CompletedProcess(
                command,
                0,
                "\n".join(
                    [
                        "0\t0\t/tmp\tbash\tactive\t\t\t100\t@10\t%10",
                        "0\t1\t/tmp\tbash\t\t\t\t101\t@10\t%11",
                        "1\t0\t/tmp\tbash\tactive\t\t\t102\t@11\t%12",
                        "1\t1\t/tmp\tpython\t\t\t\t103\t@11\t%13",
                    ]
                ),
                "",
            )
        return subprocess.CompletedProcess(command, 1, "", "unexpected command")

    script, killed_targets = build_idle_kill_script_for_sessions(
        sessions=["alpha"],
        run_command_fn=fake_run_command,
        classify_pane_status_fn=_classify_by_pane_command,
        quote_fn=_single_quote,
    )

    assert script.splitlines() == [
        "tmux kill-window -t '@10'",
        "tmux kill-pane -t '%12'",
    ]
    assert killed_targets == [
        KilledTarget(action="window", session="alpha", window="main", detail="2 pane(s)"),
        KilledTarget(action="pane", session="alpha", window="work", detail="bash"),
    ]


def test_idle_kill_script_requires_pane_status_data() -> None:
    def fake_run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
        if "list-windows" in command:
            return subprocess.CompletedProcess(command, 0, "0\tmain\t1\tactive\t@10\n", "")
        if "list-panes" in command:
            return subprocess.CompletedProcess(command, 1, "", "pane query failed")
        return subprocess.CompletedProcess(command, 1, "", "unexpected command")

    with pytest.raises(ValueError, match="Unable to inspect tmux panes in session 'alpha'"):
        build_idle_kill_script_for_sessions(
            sessions=["alpha"],
            run_command_fn=fake_run_command,
            classify_pane_status_fn=_classify_by_pane_command,
            quote_fn=_single_quote,
        )


def test_choose_idle_kill_with_all_uses_all_sessions(monkeypatch: pytest.MonkeyPatch) -> None:
    observed_sessions: list[list[str]] = []

    def fake_list_session_names() -> list[str]:
        return ["alpha", "beta"]

    def fake_build_idle_kill_script_for_sessions(
        sessions: list[str],
        run_command_fn: Callable[[list[str]], subprocess.CompletedProcess[str]],
        classify_pane_status_fn: Callable[[dict[str, str]], tuple[str, str]],
        quote_fn: Callable[[str], str],
    ) -> tuple[str, list[KilledTarget]]:
        _ = run_command_fn, classify_pane_status_fn, quote_fn
        observed_sessions.append(sessions)
        return "tmux kill-pane -t %1", []

    monkeypatch.setattr(_tmux_backend, "list_session_names", fake_list_session_names)
    monkeypatch.setattr(
        _tmux_backend,
        "build_idle_kill_script_for_sessions",
        fake_build_idle_kill_script_for_sessions,
    )

    action, payload, killed_targets = _tmux_backend.choose_kill_target(
        name=None,
        kill_all=True,
        idle=True,
        window=False,
    )

    assert action == "run_script"
    assert payload == "tmux kill-pane -t %1"
    assert killed_targets == []
    assert observed_sessions == [["alpha", "beta"]]
