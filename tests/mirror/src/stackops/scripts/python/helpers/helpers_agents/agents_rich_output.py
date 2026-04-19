

from pathlib import Path

from rich.console import Console

from stackops.scripts.python.helpers.helpers_agents.agents_rich_output import build_agents_create_overview_panel, build_generated_agents_table


def _render_text(renderable: object) -> str:
    console = Console(width=120, record=True)
    console.print(renderable)
    return console.export_text()


def test_build_agents_create_overview_panel_renders_repo_relative_values(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    agents_dir = repo_root / ".ai" / "agents" / "job"
    agents_dir.mkdir(parents=True)

    panel = build_agents_create_overview_panel(
        repo_root=repo_root,
        agents_dir=agents_dir,
        job_name="job",
        agent="codex",
        host="local",
        provider=None,
        model=None,
        reasoning_effort=None,
        agent_load=3,
        join_prompt_and_context=True,
    )

    rendered = _render_text(panel)
    assert "./.ai/agents/job" in rendered
    assert "agent default" in rendered
    assert "joined prompt/context" in rendered


def test_build_generated_agents_table_uses_file_placeholders_and_names(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    prompt_root = repo_root / "prompts"
    agent_0 = prompt_root / "agent_0"
    agent_1 = prompt_root / "agent_1"
    agent_0.mkdir(parents=True)
    agent_1.mkdir(parents=True)
    (agent_0 / "agent_0_prompt.txt").write_text("prompt", encoding="utf-8")
    (agent_0 / "agent_0_cmd.sh").write_text("cmd", encoding="utf-8")
    (agent_1 / "agent_1_material.txt").write_text("material", encoding="utf-8")

    table = build_generated_agents_table(repo_root=repo_root, prompt_dirs=[agent_0, agent_1])

    rendered = _render_text(table)
    assert "agent_0_prompt.txt | embedded | agent_0_cmd.sh" in rendered
    assert "- | agent_1_material.txt | -" in rendered
    assert "./prompts/agent_0" in rendered
