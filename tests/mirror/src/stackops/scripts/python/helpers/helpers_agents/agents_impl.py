from dataclasses import dataclass
from pathlib import Path

import pytest

import stackops.scripts.python.helpers.helpers_agents.agents_impl as agents_impl


@dataclass(frozen=True, slots=True)
class _PromptInput:
    prompt_text: str
    source_kind: str
    source_path: Path | None
    source_name: str | None


@dataclass(frozen=True, slots=True)
class _ContextInput:
    prompt_materials: list[str]
    source_kind: str
    source_path: Path | None
    file_content: str | None
    directory_entries: tuple[object, ...]


@dataclass(frozen=True, slots=True)
class _ArtifactsOutput:
    artifacts_dir: Path
    recreate_script_path: Path


def test_agents_create_drops_unsupported_reasoning_before_artifacts(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured_reasoning: list[str | None] = []

    monkeypatch.setattr(agents_impl, "show_agents_create_overview", lambda **kwargs: captured_reasoning.append(kwargs["reasoning_effort"]))
    monkeypatch.setattr(agents_impl, "show_generated_agents_table", lambda **kwargs: None)
    monkeypatch.setattr(agents_impl, "show_created_artifacts_panel", lambda **kwargs: None)
    monkeypatch.setattr("stackops.utils.accessories.get_repo_root", lambda _path: tmp_path)
    monkeypatch.setattr(agents_impl, "resolve_agents_output_dir", lambda repo_root, agents_dir, job_name: (tmp_path / "agents", "job"))
    monkeypatch.setattr(agents_impl, "resolve_agents_workspace_root", lambda preferred_root, agents_dir_obj: preferred_root)
    monkeypatch.setattr(
        agents_impl,
        "resolve_prompt_input",
        lambda prompt, prompt_path, prompt_name: _PromptInput(
            prompt_text="prompt",
            source_kind="inline_text",
            source_path=None,
            source_name=None,
        ),
    )
    monkeypatch.setattr(
        agents_impl,
        "resolve_context_input",
        lambda context, context_path, separator, agent_load, agents_dir_obj: _ContextInput(
            prompt_materials=["context"],
            source_kind="inline_text",
            source_path=None,
            file_content="context",
            directory_entries=(),
        ),
    )
    monkeypatch.setattr(
        "stackops.scripts.python.helpers.helpers_agents.fire_agents_help_launch.prep_agent_launch",
        lambda **kwargs: captured_reasoning.append(kwargs["reasoning_effort"]),
    )
    monkeypatch.setattr(
        "stackops.scripts.python.helpers.helpers_agents.fire_agents_help_launch.get_prompt_directories",
        lambda prompt_root: [prompt_root / "agent_0"],
    )
    monkeypatch.setattr(
        "stackops.scripts.python.helpers.helpers_agents.fire_agents_help_launch.get_agents_launch_layout",
        lambda session_root, job_name, start_dir: {"layoutName": job_name},
    )
    monkeypatch.setattr(
        agents_impl,
        "write_create_artifacts",
        lambda **kwargs: captured_reasoning.append(kwargs["reasoning_effort"])
        or _ArtifactsOutput(
            artifacts_dir=tmp_path / "artifacts",
            recreate_script_path=tmp_path / "recreate.sh",
        ),
    )

    agents_impl.agents_create(
        agent="claude",
        model=None,
        agent_load=1,
        context="context",
        context_path=None,
        separator="\n@-@\n",
        prompt="prompt",
        prompt_path=None,
        prompt_name=None,
        job_name="job",
        join_prompt_and_context=False,
        output_path=str(tmp_path / "layout.json"),
        agents_dir=str(tmp_path / "agents"),
        host="local",
        reasoning_effort="high",
        provider=None,
        interactive=False,
    )

    assert captured_reasoning == [None, None, None]
