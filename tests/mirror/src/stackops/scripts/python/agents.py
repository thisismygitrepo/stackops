from typing import cast

import pytest
from typer.testing import CliRunner

import stackops.scripts.python.agents as agents_app
from stackops.scripts.python.helpers.helpers_agents import agents_impl
from stackops.scripts.python.helpers.helpers_agents import agents_skill_impl


def test_add_config_uses_current_directory_when_root_is_omitted(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_calls: list[dict[str, object]] = []

    def fake_init_config(
        *,
        root: str | None,
        frameworks: tuple[object, ...],
        include_common: bool,
        add_all_configs_to_gitignore: bool,
        add_lint_task: bool,
        add_config: bool,
        add_instructions: bool,
    ) -> None:
        captured_calls.append(
            {
                "root": root,
                "frameworks": frameworks,
                "include_common": include_common,
                "add_all_configs_to_gitignore": add_all_configs_to_gitignore,
                "add_lint_task": add_lint_task,
                "add_config": add_config,
                "add_instructions": add_instructions,
            }
        )

    monkeypatch.setattr(agents_impl, "init_config", fake_init_config)

    result = CliRunner().invoke(agents_app.get_app(), ["add-config", "--agent", "copilot"])

    assert result.exit_code == 0
    assert captured_calls == [
        {
            "root": None,
            "frameworks": ("copilot",),
            "include_common": False,
            "add_all_configs_to_gitignore": False,
            "add_lint_task": False,
            "add_config": True,
            "add_instructions": True,
        }
    ]


def test_add_config_accepts_negative_boolean_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_calls: list[dict[str, object]] = []

    def fake_init_config(
        *,
        root: str | None,
        frameworks: tuple[object, ...],
        include_common: bool,
        add_all_configs_to_gitignore: bool,
        add_lint_task: bool,
        add_config: bool,
        add_instructions: bool,
    ) -> None:
        captured_calls.append(
            {
                "root": root,
                "frameworks": frameworks,
                "include_common": include_common,
                "add_all_configs_to_gitignore": add_all_configs_to_gitignore,
                "add_lint_task": add_lint_task,
                "add_config": add_config,
                "add_instructions": add_instructions,
            }
        )

    monkeypatch.setattr(agents_impl, "init_config", fake_init_config)

    result = CliRunner().invoke(
        agents_app.get_app(),
        ["add-config", "--agent", "copilot", "--no-add-config", "--no-add-instructions"],
    )

    assert result.exit_code == 0
    assert len(captured_calls) == 1
    call = captured_calls[0]
    assert cast(tuple[str, ...], call["frameworks"]) == ("copilot",)
    assert call["add_config"] is False
    assert call["add_instructions"] is False


def test_add_skill_propagates_nonzero_exit_code(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_add_skill(*, skill_name: str | None, agent: str | None, scope: str, directory: str | None) -> int:
        del skill_name, agent, scope, directory
        return 23

    monkeypatch.setattr(agents_skill_impl, "add_skill", fake_add_skill)

    result = CliRunner().invoke(agents_app.get_app(), ["add-skill", "agent-browser"])

    assert result.exit_code == 23
