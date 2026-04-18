from pathlib import Path
from typing import cast

import pytest

from stackops.scripts.python.helpers.helpers_agents.agentic_frameworks import fire_cursor_agents
from stackops.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AI_SPEC


def _build_ai_spec(*, machine: str) -> AI_SPEC:
    return cast(
        AI_SPEC,
        {
            "machine": machine,
            "api_spec": {"api_key": None},
        },
    )


@pytest.mark.parametrize("machine", ["local", "docker"])
def test_fire_cursor_returns_expected_command_for_all_hosts(machine: str, tmp_path: Path) -> None:
    prompt_path = tmp_path / "prompt.md"

    command = fire_cursor_agents.fire_cursor(_build_ai_spec(machine=machine), prompt_path)

    assert "cursor-agent --print --output-format text" in command
    assert str(prompt_path) in command
