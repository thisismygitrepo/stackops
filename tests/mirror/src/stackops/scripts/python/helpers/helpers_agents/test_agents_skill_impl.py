from stackops.scripts.python.helpers.helpers_agents.agents_skill_impl import (
    build_agent_skill_install_commands,
    supported_agent_skill_names,
)


def test_recently_added_open_source_skill_names_are_supported() -> None:
    assert {"agent-skills", "last30days"} <= set(supported_agent_skill_names())


def test_agent_skills_builds_skills_cli_install_command() -> None:
    commands = build_agent_skill_install_commands(
        skill_names=("agent-skills",), agent_targets=("codex",), scope="global", backend="bunx"
    )

    assert commands == (
        (
            "bunx",
            "skills@latest",
            "add",
            "addyosmani/agent-skills",
            "--yes",
            "--global",
            "--agent",
            "codex",
        ),
    )


def test_last30days_builds_npx_skills_cli_install_command() -> None:
    commands = build_agent_skill_install_commands(
        skill_names=("last30days",), agent_targets=("codex",), scope="global", backend="npx"
    )

    assert commands == (
        (
            "npx",
            "skills@latest",
            "add",
            "mvanhorn/last30days-skill",
            "--yes",
            "--global",
            "--agent",
            "codex",
        ),
    )
