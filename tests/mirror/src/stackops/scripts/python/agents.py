from typing import Literal, get_args

import pytest
from typer.testing import CliRunner

from stackops.scripts.python import agents
from stackops.scripts.python.helpers.helpers_agents import agents_impl, agents_skill_impl
from stackops.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AGENTS


def test_add_skill_without_name_reaches_interactive_impl(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_calls: list[tuple[str | None, str | None, Literal["local", "global"], str | None]] = []

    def fake_add_skill(*, skill_name: str | None, agent: str | None, scope: Literal["local", "global"], directory: str | None) -> None:
        captured_calls.append((skill_name, agent, scope, directory))

    monkeypatch.setattr(agents_skill_impl, "add_skill", fake_add_skill)

    result = CliRunner().invoke(agents.get_app(), ["add-skill"])

    assert result.exit_code == 0
    assert captured_calls == [(None, None, "local", None)]


def test_init_config_requires_agent_option() -> None:
    result = CliRunner().invoke(agents.get_app(), ["g", "--root", "."])

    assert result.exit_code == 2
    assert "Missing option '--agent'" in result.output


def test_init_config_all_maps_to_every_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_calls: list[tuple[str | None, tuple[AGENTS, ...], bool, bool, bool, bool, bool]] = []

    def fake_init_config(
        *,
        root: str | None,
        frameworks: tuple[AGENTS, ...],
        include_common: bool,
        add_all_configs_to_gitignore: bool,
        add_lint_task: bool,
        add_config: bool,
        add_instructions: bool,
    ) -> None:
        captured_calls.append((root, frameworks, include_common, add_all_configs_to_gitignore, add_lint_task, add_config, add_instructions))

    monkeypatch.setattr(agents_impl, "init_config", fake_init_config)

    result = CliRunner().invoke(agents.get_app(), ["g", "--root", ".", "--agent", "all"])

    assert result.exit_code == 0
    assert captured_calls == [(".", get_args(AGENTS), False, False, False, True, True)]


def test_init_config_rejects_mixing_all_with_specific_agents() -> None:
    result = CliRunner().invoke(agents.get_app(), ["g", "--root", ".", "--agent", "all,codex"])

    assert result.exit_code == 2
    assert "Do not mix 'all' with specific agent names" in result.output
