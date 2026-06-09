from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_agents.agents_skill_impl import (
    build_agent_skill_install_commands,
    is_supported_agent_skill_name,
    parse_requested_skill_agent_targets,
    render_agent_skill_install_script,
    supported_agent_skill_names,
)


def test_stackops_skill_is_supported() -> None:
    assert is_supported_agent_skill_name(skill_name="stackops")
    assert "stackops" in supported_agent_skill_names()


def test_stackops_skill_install_command_selects_repo_skill() -> None:
    assert build_agent_skill_install_commands(skill_names=("stackops",), agent_targets=(), scope="local") == (
        ("bunx", "skills@latest", "add", "https://github.com/thisismygitrepo/stackops", "--skill", "stackops", "--yes"),
    )


def test_existing_skill_install_command_shape_is_preserved() -> None:
    assert build_agent_skill_install_commands(skill_names=("caveman",), agent_targets=("codex",), scope="global") == (
        ("bunx", "skills@latest", "add", "JuliusBrussee/caveman", "--yes", "--global", "--agent", "codex"),
    )


def test_agent_targets_are_comma_separated_without_empty_entries() -> None:
    assert parse_requested_skill_agent_targets(raw_value="codex,github-copilot") == ("codex", "github-copilot")
    with pytest.raises(ValueError, match="without empty entries"):
        parse_requested_skill_agent_targets(raw_value="codex,")


def test_render_install_script_quotes_install_root() -> None:
    script = render_agent_skill_install_script(
        install_root=Path("/tmp/StackOps Skills"),
        commands=build_agent_skill_install_commands(skill_names=("stackops",), agent_targets=("codex",), scope="local"),
    )

    assert script.startswith("cd '/tmp/StackOps Skills'\n")
    assert "bunx skills@latest add https://github.com/thisismygitrepo/stackops --skill stackops --yes --agent codex" in script
