from typing import Literal

import pytest
from typer.testing import CliRunner

from stackops.scripts.python import agents
from stackops.scripts.python.helpers.helpers_agents import agents_skill_impl


def test_add_skill_without_name_reaches_interactive_impl(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_calls: list[tuple[str | None, str | None, Literal["local", "global"], str | None]] = []

    def fake_add_skill(*, skill_name: str | None, agent: str | None, scope: Literal["local", "global"], directory: str | None) -> None:
        captured_calls.append((skill_name, agent, scope, directory))

    monkeypatch.setattr(agents_skill_impl, "add_skill", fake_add_skill)

    result = CliRunner().invoke(agents.get_app(), ["add-skill"])

    assert result.exit_code == 0
    assert captured_calls == [(None, None, "local", None)]
