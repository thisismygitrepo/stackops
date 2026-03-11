from pathlib import Path

from machineconfig.cluster.sessions_managers.tmux.tmux_utils.tmux_helpers import build_tmux_commands
from machineconfig.scripts.python.helpers.helpers_cloud.cloud_mont_tmux import build_tmux_launch_command
from machineconfig.scripts.python.helpers.helpers_sessions import sessions_dynamic


def test_build_tmux_commands_targets_session_for_new_windows() -> None:
    layout = {
        "layoutName": "demo",
        "layoutTabs": [
            {"tabName": "one", "startDir": "~", "command": "echo one"},
            {"tabName": "two", "startDir": "~", "command": "echo two"},
        ],
    }

    commands = build_tmux_commands(layout, "demo")

    assert commands[2] == f"tmux new-window -t demo: -n two -c {Path.home()}"


def test_build_tmux_launch_command_uses_session_target_without_hardcoded_zero() -> None:
    command = build_tmux_launch_command(
        mount_commands={"cloudA": "echo mount", "cloudB": "echo mount2"},
        mount_locations={"cloudA": "/tmp/a", "cloudB": "/tmp/b"},
        session_name="demo",
    )

    assert "tmux rename-window -t demo: cloudA" in command
    assert "tmux new-window -t demo: -n cloudB" in command
    assert "rename-window -t demo:0" not in command


def test_spawn_tab_tmux_targets_session_namespace(monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_run_tmux_command(args: list[str]) -> None:
        calls.append(args)

    monkeypatch.setattr(sessions_dynamic, "_run_tmux_command", fake_run_tmux_command)

    sessions_dynamic._spawn_tab_tmux(
        "demo",
        {
            "index": 0,
            "runtime_tab_name": "two__dynamic_1",
            "tab": {"tabName": "two__dynamic_1", "startDir": "/tmp", "command": "echo two"},
        },
    )

    assert calls[0] == ["new-window", "-t", "demo:", "-n", "two__dynamic_1", "-c", "/tmp"]
    assert calls[1] == ["send-keys", "-t", "demo:two__dynamic_1", "echo two", "C-m"]
