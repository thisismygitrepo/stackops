from __future__ import annotations

import subprocess

import pytest

from machineconfig.cluster.sessions_managers.zellij.zellij_utils import zellij_local_helper_restart as subject
from machineconfig.utils.schemas.layouts.layout_types import LayoutConfig


def _make_layout_config(command: str) -> LayoutConfig:
    return {"layoutName": "Restart", "layoutTabs": [{"tabName": "worker", "startDir": "/repo", "command": command}]}


class EchoConsole:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def print(self, message: str) -> None:
        self.messages.append(message)
        print(message)


def test_restart_tab_process_returns_false_for_unknown_tab(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    fake_console = EchoConsole()
    monkeypatch.setattr(subject, "console", fake_console)

    result = subject.restart_tab_process("missing", _make_layout_config("python worker.py"), "main-session")

    output = capsys.readouterr().out
    assert result is False
    assert "Tab 'missing' not found in layout" in output
    assert fake_console.messages == ["[bold red]❌ Tab 'missing' not found in layout[/bold red]"]


def test_restart_tab_process_replays_expected_zellij_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    sleeps: list[float] = []
    monkeypatch.setattr(subject, "console", EchoConsole())

    def fake_run(command: str, shell: bool, check: bool, capture_output: bool, text: bool) -> subprocess.CompletedProcess[str]:
        assert shell is True
        assert check is True
        assert capture_output is True
        assert text is True
        calls.append(command)
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subject.subprocess, "run", fake_run)
    monkeypatch.setattr(subject.time, "sleep", lambda seconds: sleeps.append(seconds))

    result = subject.restart_tab_process("worker", _make_layout_config("python worker.py --port 9000"), "main-session")

    assert result is True
    assert calls == [
        "zellij --session main-session action go-to-tab-name 'worker'",
        "zellij --session main-session action write-chars '\\u0003'",
        "zellij --session main-session action write-chars 'clear'",
        "zellij --session main-session action write-chars '\\n'",
        "zellij --session main-session action write-chars 'python worker.py --port 9000'",
        "zellij --session main-session action write-chars '\\n'",
    ]
    assert sleeps == [0.5, 0.3, 0.2]


def test_restart_tab_process_handles_subprocess_failures(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(subject, "console", EchoConsole())

    def fake_run(command: str, shell: bool, check: bool, capture_output: bool, text: bool) -> subprocess.CompletedProcess[str]:
        raise subprocess.CalledProcessError(returncode=1, cmd=command)

    monkeypatch.setattr(subject.subprocess, "run", fake_run)

    result = subject.restart_tab_process("worker", _make_layout_config("python worker.py"), "main-session")

    output = capsys.readouterr().out
    assert result is False
    assert "Failed to restart tab 'worker'" in output
