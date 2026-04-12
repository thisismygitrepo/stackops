from pathlib import Path
import subprocess

import pytest

from machineconfig.cluster.sessions_managers.tmux.tmux_utils import tmux_helpers
from machineconfig.utils.schemas.layouts.layout_types import LayoutConfig, TabConfig


def _layout() -> LayoutConfig:
    return {
        "layoutName": "demo",
        "layoutTabs": [
            {"tabName": "editor", "startDir": "/work/app", "command": "nvim"},
            {"tabName": "server", "startDir": "/work/app", "command": "uv run server.py"},
        ],
    }


def test_normalize_cwd_and_attach_command(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_home() -> Path:
        return Path("/tmp/home")

    monkeypatch.setattr(tmux_helpers.Path, "home", fake_home)

    assert tmux_helpers.normalize_cwd("$HOME/work") == "/tmp/home/work"
    assert "'alpha beta'" in tmux_helpers.build_tmux_attach_or_switch_command("alpha beta")


def test_validate_layout_config_rejects_blank_tab_name() -> None:
    bad_layout: LayoutConfig = {"layoutName": "bad", "layoutTabs": [{"tabName": " ", "startDir": "/work", "command": "echo hi"}]}

    with pytest.raises(ValueError, match="Invalid tab name"):
        tmux_helpers.validate_layout_config(bad_layout)


def test_list_tmux_window_names_handles_missing_and_other_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_missing(args: list[str], _capture_output: bool, _text: bool, _timeout: int, _check: bool) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="can't find session")

    monkeypatch.setattr(tmux_helpers.subprocess, "run", fake_missing)
    assert tmux_helpers.list_tmux_window_names("alpha") == set()

    def fake_error(args: list[str], _capture_output: bool, _text: bool, _timeout: int, _check: bool) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="permission denied")

    monkeypatch.setattr(tmux_helpers.subprocess, "run", fake_error)
    with pytest.raises(RuntimeError, match="Failed to list tmux windows"):
        tmux_helpers.list_tmux_window_names("alpha")


def test_build_tmux_commands_creates_session_windows_and_selects_first() -> None:
    commands = tmux_helpers.build_tmux_commands(layout_config=_layout(), session_name="alpha", exit_mode="backToShell")

    assert commands[0] == "tmux new-session -d -s alpha -n editor -c /work/app"
    assert "tmux new-window -t alpha: -n server -c /work/app" in commands
    assert "tmux select-window -t alpha:editor" in commands
    assert any(command.endswith("nvim C-m") for command in commands)
    assert any(command.endswith("'uv run server.py' C-m") for command in commands)


def test_build_tmux_commands_wraps_non_shell_exit_modes(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_build_tmux_exit_mode_command(command: str, exit_mode: str) -> str:
        return f"wrapped::{exit_mode}::{command}"

    monkeypatch.setattr(tmux_helpers, "build_tmux_exit_mode_command", fake_build_tmux_exit_mode_command)

    commands = tmux_helpers.build_tmux_commands(layout_config=_layout(), session_name="alpha", exit_mode="killWindow")

    assert any("wrapped::killWindow::nvim" in command for command in commands)
    assert any("wrapped::killWindow::uv run server.py" in command for command in commands)


def test_build_tmux_merge_commands_overwrite_replaces_matching_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_list_tmux_window_names(_session_name: str) -> set[str]:
        return {"editor"}

    def fake_generate_random_suffix(_length: int) -> str:
        return "abc12345"

    monkeypatch.setattr(tmux_helpers, "list_tmux_window_names", fake_list_tmux_window_names)
    monkeypatch.setattr(tmux_helpers, "generate_random_suffix", fake_generate_random_suffix)

    commands = tmux_helpers.build_tmux_merge_commands(
        layout_config=_layout(), session_name="alpha", on_conflict="mergeNewWindowsOverwriteMatchingWindows", exit_mode="backToShell"
    )

    assert any("editor__machineconfig_replace__abc12345" in command for command in commands)
    assert "tmux kill-window -t alpha:editor" in commands
    assert "tmux rename-window -t alpha:editor__machineconfig_replace__abc12345 editor" in commands


def test_check_tmux_session_status_handles_no_server_and_success(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_missing(args: list[str], _capture_output: bool, _text: bool, _timeout: int) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="no server running on /tmp/tmux-1000/default")

    monkeypatch.setattr(tmux_helpers.subprocess, "run", fake_missing)
    assert tmux_helpers.check_tmux_session_status("alpha") == {
        "tmux_running": False,
        "session_exists": False,
        "session_name": "alpha",
        "all_sessions": [],
    }

    def fake_success(args: list[str], _capture_output: bool, _text: bool, _timeout: int) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="alpha\nbeta\n", stderr="")

    monkeypatch.setattr(tmux_helpers.subprocess, "run", fake_success)
    assert tmux_helpers.check_tmux_session_status("alpha") == {
        "tmux_running": True,
        "session_exists": True,
        "session_name": "alpha",
        "all_sessions": ["alpha", "beta"],
    }


def test_build_unknown_command_status_mirrors_tab_config() -> None:
    tab_config: TabConfig = {"tabName": "editor", "startDir": "/work/app", "command": "nvim"}

    assert tmux_helpers.build_unknown_command_status(tab_config) == {
        "status": "unknown",
        "running": False,
        "processes": [],
        "command": "nvim",
        "tab_name": "editor",
        "cwd": "/work/app",
    }
