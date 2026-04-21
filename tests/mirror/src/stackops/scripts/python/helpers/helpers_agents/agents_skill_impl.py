from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_agents.agents_skill_impl import (
    build_agent_skill_install_commands,
    render_agent_skill_install_script,
)


def test_build_caveman_codex_local_command() -> None:
    commands = build_agent_skill_install_commands(skill_names=("caveman",), agents=("codex",), scope="local")

    assert commands == (("bunx", "skills", "add", "JuliusBrussee/caveman", "--agent", "codex", "--yes"),)


def test_build_caveman_copilot_global_command() -> None:
    commands = build_agent_skill_install_commands(skill_names=("caveman",), agents=("copilot",), scope="global")

    assert commands == (
        ("bunx", "skills", "add", "JuliusBrussee/caveman", "--agent", "github-copilot", "--yes", "--global"),
    )


def test_build_agent_browser_uses_stackops_agent_mapping() -> None:
    commands = build_agent_skill_install_commands(skill_names=("agent-browser",), agents=("cursor-agent",), scope="local")

    assert commands == (("bunx", "skills", "add", "vercel-labs/agent-browser", "--agent", "cursor", "--yes"),)


def test_build_skill_command_rejects_unknown_skill() -> None:
    with pytest.raises(ValueError, match="Skill 'missing' is not recognized"):
        build_agent_skill_install_commands(skill_names=("missing",), agents=("codex",), scope="local")


def test_build_skill_command_rejects_unsupported_stackops_agent() -> None:
    with pytest.raises(ValueError, match="StackOps agent 'forge'"):
        build_agent_skill_install_commands(skill_names=("caveman",), agents=("forge",), scope="local")


def test_render_agent_skill_install_script_quotes_install_root() -> None:
    install_root = Path("/tmp/stackops skill root")
    script = render_agent_skill_install_script(
        install_root=install_root,
        commands=(("bunx", "skills", "add", "JuliusBrussee/caveman", "--agent", "codex", "--yes"),),
    )

    assert script == "cd '/tmp/stackops skill root'\nbunx skills add JuliusBrussee/caveman --agent codex --yes\n"
