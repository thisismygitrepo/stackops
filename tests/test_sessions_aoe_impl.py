import shlex

import pytest

from machineconfig.scripts.python.helpers.helpers_sessions.sessions_aoe_impl import (
    AoeAddInterface,
    AoeLaunchOptions,
    build_aoe_add_command,
)


def _options(**overrides: object) -> AoeLaunchOptions:
    values = {
        "aoe_bin": "aoe",
        "agent": "codex",
        "model": None,
        "provider": None,
        "sandbox": None,
        "yolo": False,
        "cmd": None,
        "extra_agent_args": (),
        "env_vars": (),
        "force": False,
        "dry_run": False,
        "sleep_inbetween": 0.0,
        "tab_command_mode": "prompt",
    }
    values.update(overrides)
    return AoeLaunchOptions(**values)


def test_build_legacy_aoe_add_command_keeps_old_flags() -> None:
    command = build_aoe_add_command(
        tab={"startDir": "/repo", "tabName": "Agent0", "command": "bash /tmp/agent_0_cmd.sh"},
        title="Agent0",
        group="Agents_part1",
        options=_options(
            model="gpt-5-codex",
            provider="openai",
            sandbox="workspace-write",
            yolo=True,
            extra_agent_args=("--search",),
            env_vars=("OPENAI_API_KEY=test",),
            force=True,
        ),
        interface=AoeAddInterface(style="legacy"),
    )

    assert command == [
        "aoe",
        "add",
        "/repo",
        "--title",
        "Agent0",
        "--group",
        "Agents_part1",
        "--agent",
        "codex",
        "--model",
        "gpt-5-codex",
        "--provider",
        "openai",
        "--prompt",
        "bash /tmp/agent_0_cmd.sh",
        "--args",
        "--search",
        "--args",
        "--sandbox",
        "--args",
        "workspace-write",
        "--args",
        "--yolo",
        "--env",
        "OPENAI_API_KEY=test",
        "--force",
    ]


def test_build_modern_aoe_add_command_maps_prompt_to_extra_args() -> None:
    command = build_aoe_add_command(
        tab={"startDir": "/repo", "tabName": "Agent0", "command": "bash /tmp/agent_0_cmd.sh"},
        title="Agent0",
        group="Agents_part1",
        options=_options(
            model="gpt-5-codex",
            provider="openai",
            sandbox="workspace-write",
            yolo=True,
            extra_agent_args=("--search",),
        ),
        interface=AoeAddInterface(style="modern"),
    )

    expected_extra_args = shlex.join(
        [
            "--model",
            "gpt-5-codex",
            "--config",
            'model_provider="openai"',
            "--sandbox",
            "workspace-write",
            "--search",
            "bash /tmp/agent_0_cmd.sh",
        ]
    )
    assert command == [
        "aoe",
        "add",
        "/repo",
        "--title",
        "Agent0",
        "--group",
        "Agents_part1",
        "--cmd",
        "codex",
        "--yolo",
        "--extra-args",
        expected_extra_args,
    ]


def test_build_modern_aoe_add_command_uses_cmd_override_for_tab_command_mode_cmd() -> None:
    command = build_aoe_add_command(
        tab={"startDir": "/repo", "tabName": "Agent0", "command": "bash /tmp/agent_0_cmd.sh"},
        title="Agent0",
        group="Agents_part1",
        options=_options(tab_command_mode="cmd"),
        interface=AoeAddInterface(style="modern"),
    )

    assert command == [
        "aoe",
        "add",
        "/repo",
        "--title",
        "Agent0",
        "--group",
        "Agents_part1",
        "--cmd",
        "codex",
        "--cmd-override",
        "bash /tmp/agent_0_cmd.sh",
    ]


def test_build_modern_aoe_add_command_rejects_provider_for_non_codex() -> None:
    with pytest.raises(ValueError, match="auto-mapped for codex sessions"):
        build_aoe_add_command(
            tab={"startDir": "/repo", "tabName": "Agent0", "command": "bash /tmp/agent_0_cmd.sh"},
            title="Agent0",
            group="Agents_part1",
            options=_options(agent="claude", provider="anthropic"),
            interface=AoeAddInterface(style="modern"),
        )
