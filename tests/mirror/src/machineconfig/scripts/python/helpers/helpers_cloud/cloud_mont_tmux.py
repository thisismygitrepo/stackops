from __future__ import annotations

import pytest

from machineconfig.scripts.python.helpers.helpers_cloud import cloud_mont_tmux


def test_build_tmux_launch_command_creates_first_and_additional_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    attach_calls: list[str] = []

    def fake_attach(session_name: str) -> str:
        attach_calls.append(session_name)
        return f"ATTACH {session_name}"

    monkeypatch.setattr(cloud_mont_tmux, "build_tmux_attach_or_switch_command", fake_attach)

    command = cloud_mont_tmux.build_tmux_launch_command(
        mount_commands={"gdrive": "mount-gdrive", "dropbox": "mount-dropbox"},
        mount_locations={"gdrive": "/mnt/gdrive", "dropbox": "/mnt/dropbox"},
        session_name="clouds",
    )
    parts = command.split(" ; ")

    assert parts[0] == "tmux new-session -d -s clouds"
    assert "tmux rename-window -t clouds: gdrive" in parts
    assert any(part.startswith("tmux send-keys -t clouds:gdrive ") for part in parts)
    assert any(part.startswith("tmux new-window -t clouds: -n dropbox ") for part in parts)
    assert "tmux select-layout -t clouds:gdrive tiled" in parts
    assert "tmux select-layout -t clouds:dropbox tiled" in parts
    assert parts[-1] == "ATTACH clouds"
    assert attach_calls == ["clouds"]


def test_build_tmux_launch_command_quotes_session_names_with_spaces(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cloud_mont_tmux, "build_tmux_attach_or_switch_command", lambda session_name: "ATTACH")

    command = cloud_mont_tmux.build_tmux_launch_command(
        mount_commands={"gdrive": "mount-gdrive"}, mount_locations={"gdrive": "/mnt/gdrive"}, session_name="cloud squad"
    )

    assert "tmux new-session -d -s 'cloud squad'" in command
    assert "tmux rename-window -t 'cloud squad:' gdrive" in command
