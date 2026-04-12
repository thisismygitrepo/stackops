from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import machineconfig.cluster.sessions_managers.windows_terminal.wt_utils.wt_helpers as wt_helpers
from machineconfig.utils.schemas.layouts.layout_types import LayoutConfig


def _completed_process(*, returncode: int, stdout: str, stderr: str) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=["pwsh"], returncode=returncode, stdout=stdout, stderr=stderr)


def _build_layout_config(first_command: str, second_command: str) -> LayoutConfig:
    return {
        "layoutName": "demo",
        "layoutTabs": [
            {"tabName": "api", "startDir": "~/code/api", "command": first_command},
            {"tabName": "worker", "startDir": "~", "command": second_command},
        ],
    }


def test_parse_command_falls_back_to_plain_split_when_shlex_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_split(command: str) -> list[str]:
        raise ValueError(f"bad command: {command}")

    monkeypatch.setattr(wt_helpers.shlex, "split", fake_split)

    executable, arguments = wt_helpers.parse_command("python app.py --watch")

    assert executable == "python"
    assert arguments == ["app.py", "--watch"]


def test_validate_layout_config_rejects_blank_tab_name() -> None:
    layout_config: LayoutConfig = {"layoutName": "bad", "layoutTabs": [{"tabName": " ", "startDir": "/tmp", "command": "python app.py"}]}

    with pytest.raises(ValueError, match="Invalid tab name"):
        wt_helpers.validate_layout_config(layout_config)


def test_generate_wt_command_string_expands_home_and_joins_tabs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured_calls: list[tuple[str, str, str]] = []

    def fake_home() -> Path:
        return tmp_path

    def fake_build_powershell_exit_mode_command_parts(command: str, exit_mode: str, shell_name: str) -> list[str]:
        captured_calls.append((command, exit_mode, shell_name))
        return [shell_name, "-NoLogo", command]

    monkeypatch.setattr(wt_helpers.Path, "home", staticmethod(fake_home))
    monkeypatch.setattr(wt_helpers, "build_powershell_exit_mode_command_parts", fake_build_powershell_exit_mode_command_parts)

    command = wt_helpers.generate_wt_command_string(_build_layout_config("python api.py", "python worker.py"), "main window", "terminate")

    assert captured_calls == [("python api.py", "terminate", wt_helpers.POWERSHELL_CMD), ("python worker.py", "terminate", wt_helpers.POWERSHELL_CMD)]
    assert command.startswith('wt -w "main window" -d ')
    assert f"{tmp_path}/code/api" in command
    assert f"new-tab -d {tmp_path}" in command
    assert " `; " in command


def test_check_wt_session_status_parses_single_json_object(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = json.dumps({"Id": 1, "ProcessName": "WindowsTerminal", "StartTime": "now"})

    def fake_run(command: list[str], *, capture_output: bool, text: bool, timeout: int) -> subprocess.CompletedProcess[str]:
        assert command[0] == wt_helpers.POWERSHELL_CMD
        assert timeout == 5
        return _completed_process(returncode=0, stdout=payload, stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    status = wt_helpers.check_wt_session_status("alpha")

    assert status["wt_running"] is True
    assert status["session_exists"] is True
    assert status["session_name"] == "alpha"
    assert len(status["all_windows"]) == 1


def test_check_command_status_parses_json_lines_from_process_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = "\n".join((json.dumps({"pid": 10, "name": "python", "start_time": "now"}), "not-json"))

    def fake_run(command: list[str], *, capture_output: bool, text: bool, timeout: int) -> subprocess.CompletedProcess[str]:
        assert command[0] == wt_helpers.POWERSHELL_CMD
        assert timeout == 5
        return _completed_process(returncode=0, stdout=payload, stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    status = wt_helpers.check_command_status("api", _build_layout_config("python api.py", "python worker.py"))

    assert status["status"] == "running"
    assert status["running"] is True
    assert status["tab_name"] == "api"
    assert status["processes"] == [{"pid": 10, "name": "python", "start_time": "now"}]
