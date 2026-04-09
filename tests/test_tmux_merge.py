from subprocess import CompletedProcess
from unittest.mock import patch

from machineconfig.cluster.sessions_managers.session_conflict import SessionLaunchPlan
from machineconfig.cluster.sessions_managers.session_exit_mode import build_tmux_exit_mode_command
from machineconfig.cluster.sessions_managers.tmux.tmux_local import TmuxLayoutGenerator
from machineconfig.cluster.sessions_managers.tmux.tmux_utils import tmux_helpers
from machineconfig.utils.schemas.layouts.layout_types import LayoutConfig


def _layout() -> LayoutConfig:
    return {
        "layoutName": "Alpha",
        "layoutTabs": [
            {
                "tabName": "existing",
                "startDir": "/tmp/existing",
                "command": "echo existing",
            },
            {
                "tabName": "fresh",
                "startDir": "/tmp/fresh",
                "command": "echo fresh",
            },
        ],
    }


def test_build_tmux_merge_commands_skip_matching_windows() -> None:
    layout = _layout()

    with patch.object(
        tmux_helpers,
        "list_tmux_window_names",
        return_value={"existing"},
    ):
        commands = tmux_helpers.build_tmux_merge_commands(
            layout_config=layout,
            session_name="Alpha",
            on_conflict="mergeNewWindowsSkipMatchingWindows",
            exit_mode="backToShell",
        )

    assert all("kill-window" not in command for command in commands)
    assert all("rename-window" not in command for command in commands)
    assert any("new-window" in command and "fresh" in command for command in commands)
    assert any("send-keys" in command and "fresh" in command for command in commands)
    assert all("existing__machineconfig_replace__" not in command for command in commands)


def test_build_tmux_merge_commands_overwrite_matching_windows() -> None:
    layout = _layout()

    with (
        patch.object(
            tmux_helpers,
            "list_tmux_window_names",
            return_value={"existing"},
        ),
        patch.object(
            tmux_helpers,
            "generate_random_suffix",
            return_value="tmp12345",
        ),
    ):
        commands = tmux_helpers.build_tmux_merge_commands(
            layout_config=layout,
            session_name="Alpha",
            on_conflict="mergeNewWindowsOverwriteMatchingWindows",
            exit_mode="backToShell",
        )

    commands_blob = "\n".join(commands)
    assert "existing__machineconfig_replace__tmp12345" in commands_blob
    assert "kill-window" in commands_blob
    assert "rename-window" in commands_blob
    assert any("new-window" in command and "fresh" in command for command in commands)
    assert any("send-keys" in command and "fresh" in command for command in commands)


def test_tmux_layout_generator_uses_merge_script_for_existing_session() -> None:
    layout = _layout()
    generator = TmuxLayoutGenerator(
        layout_config=layout,
        session_name="Alpha",
        exit_mode="backToShell",
    )
    launch_plan: SessionLaunchPlan = {
        "requested_name": "Alpha",
        "session_name": "Alpha",
        "restart_required": False,
    }

    with (
        patch(
            "machineconfig.cluster.sessions_managers.tmux.tmux_local.build_session_launch_plan",
            return_value=[launch_plan],
        ),
        patch(
            "machineconfig.cluster.sessions_managers.tmux.tmux_local.check_tmux_session_status",
            return_value={
                "tmux_running": True,
                "session_exists": True,
                "session_name": "Alpha",
                "all_sessions": ["Alpha"],
            },
        ),
        patch(
            "machineconfig.cluster.sessions_managers.tmux.tmux_local.build_tmux_merge_script",
            return_value="#!/usr/bin/env bash\nset -e\n",
        ) as build_tmux_merge_script,
        patch(
            "machineconfig.cluster.sessions_managers.tmux.tmux_local.subprocess.run",
            return_value=CompletedProcess(args=["bash"], returncode=0, stdout="", stderr=""),
        ),
    ):
        generator.run(on_conflict="mergeNewWindowsSkipMatchingWindows")

    build_tmux_merge_script.assert_called_once_with(
        layout_config=layout,
        session_name="Alpha",
        on_conflict="mergeNewWindowsSkipMatchingWindows",
        exit_mode="backToShell",
    )


def test_build_tmux_exit_mode_command_terminate_mode_prompts_for_restart_or_close() -> None:
    command = build_tmux_exit_mode_command(
        command="python -c 'print(123)'",
        exit_mode="terminate",
    )

    assert "bash -lc" in command
    assert "Press Enter to restart" in command
    assert "press Enter to close" in command
    assert "tmux kill-pane -t" in command


def test_build_tmux_merge_commands_kill_window_delays_wrapped_command_until_after_window_creation() -> None:
    layout = _layout()

    with patch.object(
        tmux_helpers,
        "list_tmux_window_names",
        return_value=set(),
    ):
        commands = tmux_helpers.build_tmux_merge_commands(
            layout_config=layout,
            session_name="Alpha",
            on_conflict="mergeNewWindowsSkipMatchingWindows",
            exit_mode="killWindow",
        )

    first_send_keys_index = next(i for i, command in enumerate(commands) if "send-keys" in command)
    assert any("new-window" in command for command in commands[:first_send_keys_index])
    assert "bash -lc" in commands[first_send_keys_index]
