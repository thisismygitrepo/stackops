from collections.abc import Sequence

import pytest
from typer.testing import CliRunner

from stackops.scripts.python import agents
from stackops.scripts.python.helpers.helpers_agents import agents_impl
from stackops.utils.schemas.fire_agents.fire_agents_types import CONFIG_AGENTS


@pytest.mark.parametrize(
    ("extra_arguments", "expected_add_agentops_skill"),
    [
        ((), True),
        (("--no-agentops-skill",), False),
    ],
)
@pytest.mark.parametrize("command_name", ["add-config", "c"])
def test_add_config_forwards_agentops_skill_default_and_opt_out(
    command_name: str,
    extra_arguments: Sequence[str],
    expected_add_agentops_skill: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    forwarded_values: list[bool] = []

    def capture_init_config(
        *,
        root: str | None,
        frameworks: tuple[CONFIG_AGENTS, ...],
        include_common: bool,
        add_all_configs_to_gitignore: bool,
        add_lint_task: bool,
        add_config: bool,
        add_instructions: bool,
        add_agentops_skill: bool,
    ) -> None:
        assert root is None
        assert frameworks == ("codex",)
        assert include_common is False
        assert add_all_configs_to_gitignore is False
        assert add_lint_task is False
        assert add_config is True
        assert add_instructions is True
        forwarded_values.append(add_agentops_skill)

    monkeypatch.setattr(agents_impl, "init_config", capture_init_config)

    result = CliRunner().invoke(agents.get_app(), [command_name, "codex", *extra_arguments])

    assert result.exit_code == 0, result.output
    assert forwarded_values == [expected_add_agentops_skill]


def test_add_config_accepts_omp(monkeypatch: pytest.MonkeyPatch) -> None:
    forwarded_frameworks: list[tuple[CONFIG_AGENTS, ...]] = []

    def capture_init_config(
        *,
        root: str | None,
        frameworks: tuple[CONFIG_AGENTS, ...],
        include_common: bool,
        add_all_configs_to_gitignore: bool,
        add_lint_task: bool,
        add_config: bool,
        add_instructions: bool,
        add_agentops_skill: bool,
    ) -> None:
        assert root is None
        assert include_common is False
        assert add_all_configs_to_gitignore is False
        assert add_lint_task is False
        assert add_config is True
        assert add_instructions is True
        assert add_agentops_skill is True
        forwarded_frameworks.append(frameworks)

    monkeypatch.setattr(agents_impl, "init_config", capture_init_config)

    result = CliRunner().invoke(agents.get_app(), ["add-config", "omp"])

    assert result.exit_code == 0, result.output
    assert forwarded_frameworks == [("omp",)]
    assert "omp" in agents._parse_init_config_agents(raw_value="all")
