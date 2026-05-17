from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_agents import agents_run_impl


def test_build_agent_command_translates_copilot_reasoning_flag() -> None:
    command_line = agents_run_impl.build_agent_command(agent="copilot", prompt_file=Path("/tmp/prompt.md"), reasoning_effort="high")

    assert "--reasoning-effort high" in command_line
    assert "--reasoning high" not in command_line


def test_should_scaffold_prompts_yaml_prefers_repo_for_default_all() -> None:
    assert agents_run_impl._should_scaffold_prompts_yaml(location_name="repo", prompts_yaml_path=None, where="all") is True
    assert agents_run_impl._should_scaffold_prompts_yaml(location_name="private", prompts_yaml_path=None, where="all") is False


def test_should_scaffold_prompts_yaml_only_creates_requested_non_repo_locations() -> None:
    assert agents_run_impl._should_scaffold_prompts_yaml(location_name="private", prompts_yaml_path=None, where="private") is True
    assert agents_run_impl._should_scaffold_prompts_yaml(location_name="public", prompts_yaml_path=None, where="public") is True
    assert agents_run_impl._should_scaffold_prompts_yaml(location_name="library", prompts_yaml_path=None, where="library") is False
    assert agents_run_impl._should_scaffold_prompts_yaml(location_name="repo", prompts_yaml_path="custom.yaml", where="all") is True


def test_should_prepare_prompts_yaml_only_when_command_needs_yaml() -> None:
    assert (
        agents_run_impl._should_prepare_prompts_yaml(
            context="inline context",
            context_path=None,
            context_name=None,
            edit=False,
            show_prompts_yaml_format=False,
        )
        is False
    )
    assert (
        agents_run_impl._should_prepare_prompts_yaml(
            context=None,
            context_path="context.md",
            context_name=None,
            edit=False,
            show_prompts_yaml_format=False,
        )
        is False
    )
    assert (
        agents_run_impl._should_prepare_prompts_yaml(
            context=None,
            context_path=None,
            context_name="backend",
            edit=False,
            show_prompts_yaml_format=False,
        )
        is True
    )
    assert (
        agents_run_impl._should_prepare_prompts_yaml(
            context=None,
            context_path=None,
            context_name=None,
            edit=False,
            show_prompts_yaml_format=False,
        )
        is True
    )


def test_run_skips_prompts_yaml_scaffolding_when_context_is_explicit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    prompt_file = tmp_path / "prompt.md"
    captured_shell_invocations: list[tuple[str, bool]] = []

    def fail_resolve_prompts_yaml_paths(*, prompts_yaml_path: str | None, where: object) -> list[tuple[str, Path]]:
        raise AssertionError("run() should not resolve prompts YAML paths when --context is provided")

    def fail_ensure_prompts_yaml_exists(*, yaml_path: Path) -> bool:
        raise AssertionError("run() should not scaffold prompts YAML when --context is provided")

    monkeypatch.setattr(agents_run_impl, "resolve_prompts_yaml_paths", fail_resolve_prompts_yaml_paths)
    monkeypatch.setattr(agents_run_impl, "ensure_prompts_yaml_exists", fail_ensure_prompts_yaml_exists)
    monkeypatch.setattr(agents_run_impl, "make_prompt_file", lambda prompt, context: prompt_file)
    monkeypatch.setattr(agents_run_impl, "_print_prompt_file_preview", lambda prompt_file: None)
    monkeypatch.setattr(agents_run_impl, "build_agent_command", lambda agent, prompt_file, reasoning_effort: "echo ok")
    monkeypatch.setattr(
        "stackops.utils.code.exit_then_run_shell_script",
        lambda script, strict: captured_shell_invocations.append((script, strict)),
    )

    agents_run_impl.run(
        prompt="check this",
        agent="copilot",
        reasoning_effort=None,
        context="inline context",
        context_path=None,
        prompts_yaml_path=None,
        context_name=None,
        where="all",
        edit=False,
        show_prompts_yaml_format=False,
    )

    assert captured_shell_invocations == [("echo ok", False)]
