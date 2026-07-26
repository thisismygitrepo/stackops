import pytest

from stackops.scripts.python.helpers.helpers_agents.agents_skill_impl import build_agent_skill_install_commands


@pytest.mark.parametrize("skill_name", ("orca-cli", "orchestration", "computer-use", "orca-linear", "orca-emulator"))
def test_orca_skills_use_the_official_repository(skill_name: str) -> None:
    commands = build_agent_skill_install_commands(skill_names=(skill_name,), agent_targets=(), scope="local", backend="npx", yes=False)

    assert commands == (("npx", "skills@latest", "add", "https://github.com/stablyai/orca", "--skill", skill_name),)
