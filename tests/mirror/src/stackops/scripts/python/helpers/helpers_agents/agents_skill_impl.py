from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_agents.agents_skill_impl import (
    build_agent_skill_install_commands,
    parse_requested_skill_agent_targets,
    render_agent_skill_install_script,
)


def test_build_caveman_local_command_lets_skills_cli_choose_agents() -> None:
    commands = build_agent_skill_install_commands(skill_names=("caveman",), agent_targets=(), scope="local")

    assert commands == (("bunx", "skills@latest", "add", "JuliusBrussee/caveman", "--yes"),)


def test_build_caveman_global_command_passes_raw_agent_target() -> None:
    commands = build_agent_skill_install_commands(skill_names=("caveman",), agent_targets=("github-copilot",), scope="global")

    assert commands == (("bunx", "skills@latest", "add", "JuliusBrussee/caveman", "--yes", "--global", "--agent", "github-copilot"),)


def test_build_agent_browser_command_passes_multiple_raw_agent_targets() -> None:
    commands = build_agent_skill_install_commands(skill_names=("agent-browser",), agent_targets=("cursor", "codex"), scope="local")

    assert commands == (("bunx", "skills@latest", "add", "vercel-labs/agent-browser", "--yes", "--agent", "cursor", "codex"),)


def test_build_grill_me_command() -> None:
    commands = build_agent_skill_install_commands(skill_names=("grill-me",), agent_targets=(), scope="local")

    assert commands == (("bunx", "skills@latest", "add", "mattpocock/skills/grill-me", "--yes"),)


def test_build_skill_command_rejects_unknown_skill() -> None:
    with pytest.raises(ValueError, match="Skill 'missing' is not recognized"):
        build_agent_skill_install_commands(skill_names=("missing",), agent_targets=(), scope="local")


def test_parse_requested_skill_agent_targets_accepts_comma_separated_values() -> None:
    assert parse_requested_skill_agent_targets(raw_value="codex, github-copilot") == ("codex", "github-copilot")


def test_parse_requested_skill_agent_targets_treats_empty_value_as_autodetect() -> None:
    assert parse_requested_skill_agent_targets(raw_value="") == ()


def test_parse_requested_skill_agent_targets_rejects_empty_entries() -> None:
    with pytest.raises(ValueError, match="Agent targets must be a comma-separated list without empty entries"):
        parse_requested_skill_agent_targets(raw_value="codex,,github-copilot")


def test_render_agent_skill_install_script_quotes_install_root() -> None:
    install_root = Path("/tmp/stackops skill root")
    script = render_agent_skill_install_script(
        install_root=install_root, commands=(("bunx", "skills@latest", "add", "JuliusBrussee/caveman", "--yes"),)
    )

    assert script == "cd '/tmp/stackops skill root'\nbunx skills@latest add JuliusBrussee/caveman --yes\n"
