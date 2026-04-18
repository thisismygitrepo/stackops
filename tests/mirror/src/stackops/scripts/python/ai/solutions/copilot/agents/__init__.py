from __future__ import annotations

from pathlib import Path

import pytest

import stackops.scripts.python.ai.solutions.copilot.agents as agents_module


@pytest.mark.parametrize(
    ("reference_name"),
    [
        agents_module.THINKING_BEAST_MODE_AGENT_PATH_REFERENCE,
        agents_module.ULTIMATE_TRANSPARENT_THINKING_BEAST_MODE_AGENT_PATH_REFERENCE,
        agents_module.DEEPRESEARCH_AGENT_PATH_REFERENCE,
    ],
)
def test_agent_reference_points_to_existing_markdown_file(reference_name: str) -> None:
    assert agents_module.__file__ is not None
    module_path = Path(agents_module.__file__)
    referenced_path = module_path.with_name(reference_name)

    assert referenced_path.is_file()
    assert referenced_path.suffix == ".md"
    assert referenced_path.stat().st_size > 0
