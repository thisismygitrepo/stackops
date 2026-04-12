from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

import machineconfig.scripts.python.helpers.helpers_agents.agents_create_artifacts as artifacts_module
from machineconfig.scripts.python.helpers.helpers_agents.agents_create_artifacts import (
    CreateContextArtifactsInput,
    CreateContextDirectoryEntry,
    CreatePromptArtifactsInput,
    _build_recreate_command_args,
    write_create_artifacts,
)


def test_write_create_artifacts_recreates_snapshots_manifest_and_script(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    agents_dir = repo_root / ".ai" / "agents" / "job"
    stale_path = agents_dir / ".create" / "stale.txt"
    stale_path.parent.mkdir(parents=True, exist_ok=True)
    stale_path.write_text("old", encoding="utf-8")
    layout_output_path = agents_dir / "layout.json"
    source_context_dir = repo_root / "context-source"
    source_context_dir.mkdir()

    monkeypatch.setattr(artifacts_module.Path, "home", lambda: home_dir)

    output = write_create_artifacts(
        repo_root=repo_root,
        agents_dir=agents_dir,
        layout_output_path=layout_output_path,
        agent="codex",
        host="local",
        model="gpt-5.4",
        reasoning_effort="high",
        provider="openai",
        agent_load=2,
        separator="\n@-@\n",
        prompt=CreatePromptArtifactsInput(source_kind="yaml_name", source_path=None, source_name="team.backend", content="Prompt body"),
        context=CreateContextArtifactsInput(
            source_kind="directory_path",
            source_path=source_context_dir,
            file_content=None,
            directory_entries=(
                CreateContextDirectoryEntry(relative_path="alpha.txt", content="A"),
                CreateContextDirectoryEntry(relative_path="nested/beta.txt", content="B"),
            ),
        ),
        job_name="job",
        join_prompt_and_context=True,
    )

    manifest = json.loads(output.manifest_path.read_text(encoding="utf-8"))
    assert not stale_path.exists()
    assert output.prompt_snapshot_path.read_text(encoding="utf-8") == "Prompt body"
    assert output.context_snapshot_path.is_dir()
    assert (output.context_snapshot_path / "alpha.txt").read_text(encoding="utf-8") == "A"
    assert (output.context_snapshot_path / "nested" / "beta.txt").read_text(encoding="utf-8") == "B"
    assert os.access(output.recreate_script_path, os.X_OK)
    assert manifest["separator_cli_value"] == "\\n@-@\\n"
    assert manifest["prompt"]["source_name"] == "team.backend"
    assert manifest["context"]["snapshot_relative_paths"] == ["alpha.txt", "nested/beta.txt"]
    assert "--prompt-name" in output.recreate_command_args
    assert "--joined-prompt-context" in output.recreate_command_args
    assert output.recreate_command.startswith(f"cd {repo_root}")


def test_build_recreate_command_args_requires_prompt_name_for_yaml_source(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="prompt_name must be provided"):
        _build_recreate_command_args(
            agent="codex",
            host="local",
            model=None,
            reasoning_effort=None,
            provider="openai",
            agent_load=1,
            separator="@-@",
            prompt_source_kind="yaml_name",
            prompt_recreate_path=tmp_path / "prompt.md",
            prompt_name=None,
            context_recreate_path=tmp_path / "context.md",
            job_name="job",
            join_prompt_and_context=False,
            layout_output_path=tmp_path / "layout.json",
            agents_dir=tmp_path / "agents",
        )
