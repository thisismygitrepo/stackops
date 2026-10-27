import pytest

from stackops.scripts.python.helpers.helpers_agents.agents_skill_impl import build_agent_skill_install_commands
from stackops.scripts.python.helpers.helpers_agents.agents_skill_types import SKILL_INSTALL_SCOPE


@pytest.mark.parametrize("skill_name", ("orca-cli", "orchestration", "computer-use", "orca-linear", "orca-emulator"))
@pytest.mark.parametrize(("scope", "scope_arguments"), [("project", ()), ("user", ("--global",))])
def test_orca_skills_use_the_official_repository(skill_name: str, scope: SKILL_INSTALL_SCOPE, scope_arguments: tuple[str, ...]) -> None:
    commands = build_agent_skill_install_commands(skill_names=(skill_name,), agent_targets=(), scope=scope, backend="npx", yes=False)

    assert commands == (("npx", "skills@latest", "add", "https://github.com/stablyai/orca", "--skill", skill_name, *scope_arguments),)
