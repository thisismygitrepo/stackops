from pathlib import Path

import pytest
from rich.console import Console

from machineconfig.scripts.python.helpers.helpers_agents.agents_rich_output import (
    build_chunking_panel,
    build_generated_agents_table,
)
from machineconfig.scripts.python.helpers.helpers_agents.fire_agents_help_launch import get_agents_launch_layout


def _render_text(*, renderable: object) -> str:
    console = Console(record=True, width=200)
    console.print(renderable)
    return console.export_text()


def test_build_generated_agents_table_renders_clean_paths(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    prompt_dir = repo_root / ".ai" / "agents" / "job" / "prompts" / "agent_12"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = prompt_dir / "agent_12_prompt.txt"
    material_path = prompt_dir / "agent_12_material.txt"
    launcher_path = prompt_dir / "agent_12_cmd.sh"
    prompt_path.write_text("prompt", encoding="utf-8")
    material_path.write_text("material", encoding="utf-8")
    launcher_path.write_text("launcher", encoding="utf-8")

    rendered = _render_text(
        renderable=build_generated_agents_table(repo_root=repo_root, prompt_dirs=[prompt_dir]),
    )

    assert "Generated Agents (1)" in rendered
    assert "agent_12" in rendered
    assert "./.ai/agents/job/prompts/agent_12" in rendered
    assert "agent_12_prompt.txt | agent_12_material.txt | agent_12_cmd.sh" in rendered
    assert "PosixPath(" not in rendered


def test_build_chunking_panel_reports_group_count() -> None:
    rendered = _render_text(
        renderable=build_chunking_panel(
            subject="prompts",
            total_items=246,
            tasks_per_prompt=10,
            generated_agents=25,
            was_chunked=True,
        )
    )

    assert "Chunking" in rendered
    assert "prompts" in rendered
    assert "246" in rendered
    assert "25" in rendered
    assert "chunked" in rendered


def test_get_agents_launch_layout_is_silent_and_naturally_sorted(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    session_root = tmp_path / "agents" / "job"
    prompt_root = session_root / "prompts"
    prompt_root.mkdir(parents=True, exist_ok=True)

    for agent_name in ("agent_10", "agent_2", "agent_1"):
        prompt_dir = prompt_root / agent_name
        prompt_dir.mkdir(parents=True, exist_ok=True)
        prompt_index = agent_name.split("_")[-1]
        command_path = prompt_dir / f"agent_{prompt_index}_cmd.sh"
        command_path.write_text("echo test", encoding="utf-8")

    layout = get_agents_launch_layout(session_root=session_root, job_name="job")
    captured = capsys.readouterr()

    assert captured.out == ""
    assert [tab["tabName"] for tab in layout["layouts"][0]["layoutTabs"]] == ["Agent1", "Agent2", "Agent10"]
