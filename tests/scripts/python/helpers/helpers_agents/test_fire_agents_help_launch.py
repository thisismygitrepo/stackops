from pathlib import Path

from machineconfig.scripts.python.helpers.helpers_agents.fire_agents_help_launch import _format_material_reference


def test_format_material_reference_returns_repo_relative_path() -> None:
    repo_root = Path("/tmp/example-repo")
    material_path = repo_root / ".ai" / "agents" / "job" / "prompts" / "agent_0" / "agent_0_material.txt"

    result = _format_material_reference(prompt_material_path=material_path, repo_root=repo_root)

    assert result == ".ai/agents/job/prompts/agent_0/agent_0_material.txt"


def test_format_material_reference_falls_back_to_absolute_path() -> None:
    repo_root = Path("/tmp/example-repo")
    material_path = Path("/tmp/external-agents/job/prompts/agent_0/agent_0_material.txt")

    result = _format_material_reference(prompt_material_path=material_path, repo_root=repo_root)

    assert result == str(material_path)
