from pathlib import Path

import pytest

from machineconfig.scripts.python.helpers.helpers_agents import agents_create_artifacts as artifacts_module
from machineconfig.scripts.python.helpers.helpers_agents.agents_create_artifacts import (
    CreateContextArtifactsInput,
    CreatePromptArtifactsInput,
    write_create_artifacts,
)


def test_write_create_artifacts_prefers_original_sources_and_portable_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home_root = tmp_path / "home" / "alex"
    repo_root = home_root / "code" / "machineconfig"
    agents_dir = repo_root / ".ai" / "agents" / "job"
    layout_output_path = agents_dir / "layout.json"
    prompt_source_path = home_root / "prompts" / "prompt.md"
    context_source_path = repo_root / "inputs" / "context.md"

    prompt_source_path.parent.mkdir(parents=True, exist_ok=True)
    context_source_path.parent.mkdir(parents=True, exist_ok=True)
    agents_dir.mkdir(parents=True, exist_ok=True)

    prompt_source_path.write_text("prompt body", encoding="utf-8")
    context_source_path.write_text("context body", encoding="utf-8")

    monkeypatch.setattr(artifacts_module.Path, "home", lambda: home_root)

    create_artifacts = write_create_artifacts(
        repo_root=repo_root,
        agents_dir=agents_dir,
        layout_output_path=layout_output_path,
        agent="codex",
        host="local",
        model="gpt-5",
        reasoning_effort="medium",
        provider="openai",
        agent_load=2,
        separator="\n---\n",
        prompt=CreatePromptArtifactsInput(
            source_kind="file_path",
            source_path=prompt_source_path,
            source_name=None,
            content="prompt body",
        ),
        context=CreateContextArtifactsInput(
            source_kind="file_path",
            source_path=context_source_path,
            file_content="context body",
            directory_entries=(),
        ),
        job_name="job",
        join_prompt_and_context=False,
    )

    recreate_script = create_artifacts.recreate_script_path.read_text(encoding="utf-8")

    assert "cd $HOME/code/machineconfig &&" in recreate_script
    assert "--context-path inputs/context.md" in recreate_script
    assert "--prompt-path $HOME/prompts/prompt.md" in recreate_script
    assert "--output-path .ai/agents/job/layout.json" in recreate_script
    assert "--agents-dir .ai/agents/job" in recreate_script
    assert str(context_source_path) not in recreate_script
    assert str(prompt_source_path) not in recreate_script
    assert str(create_artifacts.context_snapshot_path) not in recreate_script
    assert str(create_artifacts.prompt_snapshot_path) not in recreate_script

    assert str(context_source_path) in create_artifacts.recreate_command_args
    assert str(prompt_source_path) in create_artifacts.recreate_command_args
    assert str(create_artifacts.context_snapshot_path) not in create_artifacts.recreate_command_args
    assert str(create_artifacts.prompt_snapshot_path) not in create_artifacts.recreate_command_args


def test_write_create_artifacts_preserves_prompt_name_source(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    agents_dir = repo_root / ".ai" / "agents" / "job"
    layout_output_path = agents_dir / "layout.json"

    agents_dir.mkdir(parents=True, exist_ok=True)

    create_artifacts = write_create_artifacts(
        repo_root=repo_root,
        agents_dir=agents_dir,
        layout_output_path=layout_output_path,
        agent="codex",
        host="local",
        model="gpt-5",
        reasoning_effort="medium",
        provider="openai",
        agent_load=2,
        separator="\n---\n",
        prompt=CreatePromptArtifactsInput(
            source_kind="yaml_name",
            source_path=None,
            source_name="team.backend",
            content="prompt body",
        ),
        context=CreateContextArtifactsInput(
            source_kind="inline_text",
            source_path=None,
            file_content="context body",
            directory_entries=(),
        ),
        job_name="job",
        join_prompt_and_context=False,
    )

    recreate_script = create_artifacts.recreate_script_path.read_text(encoding="utf-8")

    assert "--prompt-name team.backend" in recreate_script
    assert "--prompt-path" not in recreate_script
    assert "--prompt-name" in create_artifacts.recreate_command_args
    assert "team.backend" in create_artifacts.recreate_command_args
