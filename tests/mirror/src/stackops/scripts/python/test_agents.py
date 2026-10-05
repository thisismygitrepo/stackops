from collections.abc import Sequence

import pytest
from typer.testing import CliRunner

from stackops.scripts.python import agents
from stackops.scripts.python.helpers.helpers_agents import agents_impl
from stackops.utils.schemas.fire_agents.fire_agents_types import CONFIG_AGENTS


@pytest.mark.parametrize(
    ("extra_arguments", "expected_inclusions"),
    [
        ((), (True, True, True)),
        (("--no-add-config",), (False, True, True)),
        (("-c",), (False, True, True)),
        (("--no-add-instructions",), (True, False, True)),
        (("-i",), (True, False, True)),
        (("--no-agent-ops-skill",), (True, True, False)),
        (("-a",), (True, True, False)),
        (("-c", "-i", "-a"), (False, False, False)),
    ],
)
@pytest.mark.parametrize("command_name", ["add-config", "c"])
def test_add_config_forwards_default_inclusions_and_opt_outs(
    command_name: str,
    extra_arguments: Sequence[str],
    expected_inclusions: tuple[bool, bool, bool],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    forwarded_values: list[tuple[bool, bool, bool]] = []

    def capture_init_config(
        *,
        root: str | None,
        frameworks: tuple[CONFIG_AGENTS, ...],
        include_common: bool,
        add_all_configs_to_gitignore: bool,
        add_lint_task: bool,
        add_config: bool,
        add_instructions: bool,
        add_agent_ops_skill: bool,
    ) -> None:
        assert root is None
        assert frameworks == ("codex",)
        assert include_common is False
        assert add_all_configs_to_gitignore is False
        assert add_lint_task is False
        forwarded_values.append((add_config, add_instructions, add_agent_ops_skill))

    monkeypatch.setattr(agents_impl, "init_config", capture_init_config)

    result = CliRunner().invoke(agents.get_app(), [command_name, "codex", *extra_arguments])

    assert result.exit_code == 0, result.output
    assert forwarded_values == [expected_inclusions]


@pytest.mark.parametrize("removed_flag", ["--add-config", "--add-instructions", "--agent-ops-skill", "-C", "-I", "-A"])
def test_add_config_rejects_removed_positive_flags(removed_flag: str) -> None:
    result = CliRunner().invoke(agents.get_app(), ["add-config", "codex", removed_flag])

    assert result.exit_code == 2, result.output


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
        add_agent_ops_skill: bool,
    ) -> None:
        assert root is None
        assert include_common is False
        assert add_all_configs_to_gitignore is False
        assert add_lint_task is False
        assert add_config is True
        assert add_instructions is True
        assert add_agent_ops_skill is True
        forwarded_frameworks.append(frameworks)

    monkeypatch.setattr(agents_impl, "init_config", capture_init_config)

    result = CliRunner().invoke(agents.get_app(), ["add-config", "omp"])

    assert result.exit_code == 0, result.output
    assert forwarded_frameworks == [("omp",)]
    assert "omp" in agents._parse_init_config_agents(raw_value="all")
