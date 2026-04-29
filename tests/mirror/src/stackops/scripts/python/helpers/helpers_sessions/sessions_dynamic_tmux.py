import subprocess

import pytest

from stackops.scripts.python.helpers.helpers_sessions import sessions_dynamic_tmux
from stackops.scripts.python.helpers.helpers_sessions.sessions_dynamic_display import DynamicTabTask


def test_tmux_task_running_detects_idle_shell_as_finished(monkeypatch: pytest.MonkeyPatch) -> None:
    task: DynamicTabTask = {
        "index": 0,
        "runtime_tab_name": "finished_tab",
        "tab": {"tabName": "finished_tab", "startDir": "/workspace", "command": "uv run script.py"},
    }

    def fake_run(args: list[str], capture_output: bool, text: bool, timeout: int, check: bool) -> subprocess.CompletedProcess[str]:
        assert capture_output is True
        assert text is True
        assert timeout == 30
        assert check is False
        assert args == [
            "tmux",
            "list-panes",
            "-t",
            "session_name:finished_tab",
            "-F",
            "#{pane_index}\t#{pane_current_command}\t#{?pane_dead,dead,}\t#{pane_dead_status}\t#{pane_pid}",
        ]
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="1\tbash\t\t\t123\n", stderr="")

    def fake_process_label(pane_pid: str) -> str | None:
        assert pane_pid == "123"
        return None

    monkeypatch.setattr(sessions_dynamic_tmux.subprocess, "run", fake_run)
    monkeypatch.setattr(sessions_dynamic_tmux, "find_meaningful_pane_process_label", fake_process_label)

    assert sessions_dynamic_tmux.is_task_running(session_name="session_name", task=task) is False


def test_tmux_task_running_detects_shell_child_as_active(monkeypatch: pytest.MonkeyPatch) -> None:
    task: DynamicTabTask = {
        "index": 0,
        "runtime_tab_name": "active_tab",
        "tab": {"tabName": "active_tab", "startDir": "/workspace", "command": "uv run script.py"},
    }

    def fake_run(args: list[str], capture_output: bool, text: bool, timeout: int, check: bool) -> subprocess.CompletedProcess[str]:
        assert capture_output is True
        assert text is True
        assert timeout == 30
        assert check is False
        assert args[3] == "session_name:active_tab"
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="1\tbash\t\t\t456\n", stderr="")

    def fake_process_label(pane_pid: str) -> str | None:
        assert pane_pid == "456"
        return "uv script.py"

    monkeypatch.setattr(sessions_dynamic_tmux.subprocess, "run", fake_run)
    monkeypatch.setattr(sessions_dynamic_tmux, "find_meaningful_pane_process_label", fake_process_label)

    assert sessions_dynamic_tmux.is_task_running(session_name="session_name", task=task) is True


def test_tmux_task_running_detects_missing_window_as_finished(monkeypatch: pytest.MonkeyPatch) -> None:
    task: DynamicTabTask = {
        "index": 0,
        "runtime_tab_name": "missing_tab",
        "tab": {"tabName": "missing_tab", "startDir": "/workspace", "command": "uv run script.py"},
    }

    def fake_run(args: list[str], capture_output: bool, text: bool, timeout: int, check: bool) -> subprocess.CompletedProcess[str]:
        assert capture_output is True
        assert text is True
        assert timeout == 30
        assert check is False
        return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="can't find window: missing_tab")

    monkeypatch.setattr(sessions_dynamic_tmux.subprocess, "run", fake_run)

    assert sessions_dynamic_tmux.is_task_running(session_name="session_name", task=task) is False
