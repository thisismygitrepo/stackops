from collections.abc import Sequence
from pathlib import Path
import subprocess

import pytest

from stackops.scripts.python.helpers.helpers_agents import agents_browser_tmux


def test_launch_browser_tmux_creates_named_session_windows_and_metadata(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    observed_commands: list[tuple[str, ...]] = []

    def fake_which(command_name: str) -> str | None:
        if command_name == "tmux":
            return "/usr/bin/tmux"
        return None

    def fake_run(
        command: Sequence[str],
        capture_output: bool,
        text: bool,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        command_tuple = tuple(command)
        observed_commands.append(command_tuple)
        return subprocess.CompletedProcess(args=command_tuple, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(agents_browser_tmux.shutil, "which", fake_which)
    monkeypatch.setattr(agents_browser_tmux.subprocess, "run", fake_run)
    monkeypatch.delenv("TMUX", raising=False)

    result = agents_browser_tmux.launch_browser_tmux(
        browser="chrome",
        profile_name="agent-browser",
        profile_path=tmp_path / "profile",
        port=9331,
        browser_port=41837,
        host="0.0.0.0",
        lan=True,
        browser_command=("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "--remote-debugging-port=41837"),
        relay_command=("python", "-m", "stackops.relay"),
        prompt_path=tmp_path / "prompt.md",
    )

    assert result.session_name == "stackops-browser-chrome-profile-agent-browser-p9331"
    assert result.browser_window_name == "chrome-endpoint"
    assert result.relay_window_name == "relay-p9331"
    assert result.attach_command == ("tmux", "attach-session", "-t", "stackops-browser-chrome-profile-agent-browser-p9331")
    assert ("tmux", "new-session", "-d", "-s", "stackops-browser-chrome-profile-agent-browser-p9331") in observed_commands
    assert ("tmux", "rename-window", "-t", "stackops-browser-chrome-profile-agent-browser-p9331:0", "chrome-endpoint") in observed_commands
    assert ("tmux", "new-window", "-d", "-t", "stackops-browser-chrome-profile-agent-browser-p9331:", "-n", "relay-p9331") in observed_commands
    assert (
        "tmux",
        "set-option",
        "-q",
        "-t",
        "stackops-browser-chrome-profile-agent-browser-p9331",
        "@stackops_browser_port",
        "9331",
    ) in observed_commands
    assert any(command[0:4] == ("tmux", "send-keys", "-t", "stackops-browser-chrome-profile-agent-browser-p9331:chrome-endpoint") for command in observed_commands)


def test_collect_browser_tmux_status_reads_stackops_session_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    separator = agents_browser_tmux._TMUX_FIELD_SEPARATOR

    def fake_which(command_name: str) -> str | None:
        if command_name == "tmux":
            return "/usr/bin/tmux"
        return None

    def fake_run(
        command: Sequence[str],
        capture_output: bool,
        text: bool,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        command_tuple = tuple(command)
        if command_tuple == ("tmux", "list-sessions", "-F", "#{session_name}"):
            return subprocess.CompletedProcess(
                args=command_tuple,
                returncode=0,
                stdout="stackops-browser-chrome-profile-agent-browser-p9331\nunrelated\n",
                stderr="",
            )
        if command_tuple[0:4] == ("tmux", "show-options", "-qv", "-t"):
            option_values = {
                "@stackops_browser": "chrome",
                "@stackops_browser_profile": "profile-agent-browser",
                "@stackops_browser_profile_path": "/tmp/profile",
                "@stackops_browser_host": "0.0.0.0",
                "@stackops_browser_port": "9331",
                "@stackops_browser_browser_port": "41837",
                "@stackops_browser_lan": "yes",
                "@stackops_browser_prompt_path": "/tmp/prompt.md",
            }
            return subprocess.CompletedProcess(args=command_tuple, returncode=0, stdout=f"{option_values[command_tuple[5]]}\n", stderr="")
        if command_tuple[0:4] == ("tmux", "list-panes", "-a", "-F"):
            pane_line = separator.join(
                (
                    "stackops-browser-chrome-profile-agent-browser-p9331",
                    "0",
                    "chrome-endpoint",
                    "0",
                    "%1",
                    "1234",
                    "Google Chrome",
                    "0",
                    "/Users/alex/code/stackops",
                )
            )
            return subprocess.CompletedProcess(args=command_tuple, returncode=0, stdout=f"{pane_line}\n", stderr="")
        return subprocess.CompletedProcess(args=command_tuple, returncode=1, stdout="", stderr="unexpected command")

    monkeypatch.setattr(agents_browser_tmux.shutil, "which", fake_which)
    monkeypatch.setattr(agents_browser_tmux.subprocess, "run", fake_run)

    rows = agents_browser_tmux.collect_browser_tmux_status()

    assert len(rows) == 1
    row = rows[0]
    assert row.session_name == "stackops-browser-chrome-profile-agent-browser-p9331"
    assert row.window_name == "chrome-endpoint"
    assert row.pane_pid == "1234"
    assert not row.pane_dead
    assert row.metadata.browser == "chrome"
    assert row.metadata.host == "0.0.0.0"
    assert row.metadata.browser_port == "41837"
