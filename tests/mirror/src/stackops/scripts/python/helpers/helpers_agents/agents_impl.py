from __future__ import annotations

from pathlib import Path

import pytest

import stackops.scripts.python.helpers.helpers_agents.agents_impl as agents_impl_module
from stackops.scripts.python.helpers.helpers_agents.agents_create_artifacts import CreateArtifactsOutput
from stackops.scripts.python.helpers.helpers_agents.agents_create_inputs import ResolvedContextInput, ResolvedPromptInput


def test_collect_concatenates_material_files_in_numeric_order(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    prompts_dir = tmp_path / "agents" / "prompts"
    for name, content in (("agent_10", "ten"), ("agent_2", "two"), ("agent_1", "one")):
        agent_dir = prompts_dir / name
        agent_dir.mkdir(parents=True)
        (agent_dir / f"{name}_material.txt").write_text(content, encoding="utf-8")
    output_path = tmp_path / "out" / "combined.txt"

    agents_impl_module.collect(str(tmp_path / "agents"), str(output_path), "\nSEP\n", None)

    assert output_path.read_text(encoding="utf-8") == "one\nSEP\ntwo\nSEP\nten"
    assert "Found 3 material files" in capsys.readouterr().out


def test_agents_create_normalizes_codex_provider_and_writes_layout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    agents_dir = repo_root / ".ai" / "agents" / "job"
    prompt_dir = agents_dir / "prompts" / "agent_0"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "agent_0_prompt.txt").write_text("prompt", encoding="utf-8")
    captured_provider: list[str | None] = []

    monkeypatch.setattr(agents_impl_module, "show_agents_create_overview", lambda **_kwargs: None)
    monkeypatch.setattr(agents_impl_module, "show_generated_agents_table", lambda **_kwargs: None)
    monkeypatch.setattr(agents_impl_module, "show_created_artifacts_panel", lambda **_kwargs: None)
    monkeypatch.setattr(agents_impl_module, "resolve_agents_output_dir", lambda **_kwargs: (agents_dir, "job"))
    monkeypatch.setattr(
        agents_impl_module,
        "resolve_prompt_input",
        lambda **_kwargs: ResolvedPromptInput(prompt_text="Prompt prefix", source_kind="inline_text", source_path=None, source_name=None),
    )
    monkeypatch.setattr(
        agents_impl_module,
        "resolve_context_input",
        lambda **_kwargs: ResolvedContextInput(
            prompt_materials=["Task one"], source_kind="inline_text", source_path=None, file_content="Task one", directory_entries=()
        ),
    )

    def fake_prep_agent_launch(**kwargs: object) -> None:
        captured_provider.append(kwargs["provider"] if "provider" in kwargs else None)

    monkeypatch.setattr("stackops.utils.accessories.get_repo_root", lambda _cwd: repo_root)
    monkeypatch.setattr("stackops.scripts.python.helpers.helpers_agents.fire_agents_help_launch.prep_agent_launch", fake_prep_agent_launch)
    monkeypatch.setattr(
        "stackops.scripts.python.helpers.helpers_agents.fire_agents_help_launch.get_prompt_directories",
        lambda *, prompt_root: [prompt_root / "agent_0"],
    )
    monkeypatch.setattr(
        "stackops.scripts.python.helpers.helpers_agents.fire_agents_help_launch.get_agents_launch_layout",
        lambda **_kwargs: {"version": "1.0", "layouts": [{"layoutName": "job", "layoutTabs": []}]},
    )
    monkeypatch.setattr(
        agents_impl_module,
        "write_create_artifacts",
        lambda **_kwargs: CreateArtifactsOutput(
            artifacts_dir=agents_dir / ".create",
            prompt_snapshot_path=agents_dir / ".create" / "prompt.md",
            context_snapshot_path=agents_dir / ".create" / "context.md",
            manifest_path=agents_dir / ".create" / "manifest.json",
            recreate_script_path=agents_dir / ".create" / "recreate.sh",
            recreate_command="echo recreate",
            recreate_command_args=("echo", "recreate"),
        ),
    )

    agents_impl_module.agents_create(
        agent="codex",
        model="gpt-5.4",
        agent_load=1,
        context="context",
        context_path=None,
        separator="\n@-@\n",
        prompt="prompt",
        prompt_path=None,
        prompt_name=None,
        job_name=None,
        join_prompt_and_context=False,
        output_path=None,
        agents_dir=None,
        host="local",
        reasoning_effort=None,
        provider=None,
        interactive=False,
    )

    assert captured_provider == ["openai"]
    layout_path = agents_dir / "layout.json"
    assert layout_path.exists()
    assert '"layoutName": "job"' in layout_path.read_text(encoding="utf-8")
