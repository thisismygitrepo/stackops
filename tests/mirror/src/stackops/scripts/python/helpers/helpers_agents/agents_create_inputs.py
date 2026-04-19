

from pathlib import Path

import pytest

import stackops.scripts.python.helpers.helpers_agents.agents_create_inputs as inputs_module
import stackops.utils.accessories as accessories


def test_resolve_prompt_input_supports_named_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(inputs_module, "resolve_named_prompts_yaml_entry", lambda **_kwargs: "Prompt from yaml")

    resolved = inputs_module.resolve_prompt_input(prompt=None, prompt_path=None, prompt_name="team.backend")

    assert resolved.prompt_text == "Prompt from yaml"
    assert resolved.source_kind == "yaml_name"
    assert resolved.source_name == "team.backend"


def test_resolve_context_input_directory_uses_only_non_empty_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    context_dir = tmp_path / "context"
    context_dir.mkdir()
    (context_dir / "alpha.txt").write_text("alpha", encoding="utf-8")
    (context_dir / "blank.txt").write_text("   ", encoding="utf-8")
    nested_dir = context_dir / "nested"
    nested_dir.mkdir()
    (nested_dir / "beta.txt").write_text("beta", encoding="utf-8")
    chunking_calls: list[tuple[str, int, int, int, bool]] = []

    def fake_show_chunking_panel(*, subject: str, total_items: int, tasks_per_prompt: int, generated_agents: int, was_chunked: bool) -> None:
        chunking_calls.append((subject, total_items, tasks_per_prompt, generated_agents, was_chunked))

    monkeypatch.setattr(inputs_module, "show_chunking_panel", fake_show_chunking_panel)

    resolved = inputs_module.resolve_context_input(
        context=None, context_path=str(context_dir), separator="\n@-@\n", agent_load=1, agents_dir_obj=tmp_path / "agents"
    )

    assert resolved.prompt_materials == ["alpha", "beta"]
    assert resolved.source_kind == "directory_path"
    assert [entry.relative_path for entry in resolved.directory_entries] == ["alpha.txt", "blank.txt", "nested/beta.txt"]
    assert chunking_calls == [("directory files", 2, 1, 2, True)]


def test_resolve_agents_output_dir_uses_trimmed_job_name_and_randstr(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_randstr(*_args: object, **_kwargs: object) -> str:
        return "abc123"

    monkeypatch.setattr(accessories, "randstr", fake_randstr)

    generated_dir, generated_name = inputs_module.resolve_agents_output_dir(repo_root=tmp_path, agents_dir=None, job_name=None)
    explicit_dir, explicit_name = inputs_module.resolve_agents_output_dir(
        repo_root=tmp_path, agents_dir=str(tmp_path / "custom-agents"), job_name="  named-job  "
    )

    assert generated_dir == tmp_path / ".ai" / "agents" / "abc123"
    assert generated_name == "abc123"
    assert explicit_dir == (tmp_path / "custom-agents").resolve().absolute()
    assert explicit_name == "named-job"


def test_resolve_agents_workspace_root_prefers_explicit_agents_dir_when_outside_root(tmp_path: Path) -> None:
    preferred_root = tmp_path / "repo"
    preferred_root.mkdir()
    external_agents_dir = tmp_path / "scratch" / "agents"

    resolved_workspace_root = inputs_module.resolve_agents_workspace_root(
        preferred_root=preferred_root,
        agents_dir_obj=external_agents_dir,
    )

    assert resolved_workspace_root == external_agents_dir.resolve()


def test_resolve_agents_workspace_root_keeps_repo_root_for_default_agents_dir(tmp_path: Path) -> None:
    preferred_root = tmp_path / "repo"
    agents_dir = preferred_root / ".ai" / "agents" / "job"
    preferred_root.mkdir()

    resolved_workspace_root = inputs_module.resolve_agents_workspace_root(
        preferred_root=preferred_root,
        agents_dir_obj=agents_dir,
    )

    assert resolved_workspace_root == preferred_root.resolve()
