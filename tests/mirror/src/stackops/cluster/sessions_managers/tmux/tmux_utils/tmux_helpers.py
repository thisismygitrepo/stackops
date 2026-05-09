import pytest

from stackops.cluster.sessions_managers.tmux.tmux_utils import tmux_helpers
from stackops.utils.schemas.layouts.layout_types import LayoutConfig


def test_build_tmux_commands_sends_each_tab_command_once() -> None:
    layout_config: LayoutConfig = {
        "layoutName": "demo",
        "layoutTabs": [
            {"tabName": "Agent0", "startDir": "/tmp", "command": "echo zero"},
            {"tabName": "Agent1", "startDir": "/tmp", "command": "echo one"},
            {"tabName": "Agent2", "startDir": "/tmp", "command": "echo two"},
        ],
    }

    commands = tmux_helpers.build_tmux_commands(
        layout_config=layout_config,
        session_name="demo",
        exit_mode="backToShell",
    )

    send_commands = [command for command in commands if command.startswith("tmux send-keys")]

    assert send_commands == [
        "tmux send-keys -t demo:Agent0 'echo zero' C-m",
        "tmux send-keys -t demo:Agent1 'echo one' C-m",
        "tmux send-keys -t demo:Agent2 'echo two' C-m",
    ]


def test_build_tmux_merge_commands_sends_replaced_window_command_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    layout_config: LayoutConfig = {
        "layoutName": "demo",
        "layoutTabs": [
            {"tabName": "Agent1", "startDir": "/tmp", "command": "echo one"},
            {"tabName": "Agent2", "startDir": "/tmp", "command": "echo two"},
        ],
    }

    monkeypatch.setattr(tmux_helpers, "list_tmux_window_names", lambda session_name: {"Agent1"})

    commands = tmux_helpers.build_tmux_merge_commands(
        layout_config=layout_config,
        session_name="demo",
        on_conflict="mergeOverwrite",
        exit_mode="backToShell",
    )

    send_commands = [command for command in commands if command.startswith("tmux send-keys")]

    assert send_commands == [
        "tmux send-keys -t demo:Agent1 'echo one' C-m",
        "tmux send-keys -t demo:Agent2 'echo two' C-m",
    ]