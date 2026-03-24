from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from machineconfig.scripts.python import agents
from machineconfig.scripts.python.helpers.helpers_agents import agent_impl_interactive
from machineconfig.scripts.python.helpers.helpers_agents import agents_impl
from machineconfig.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_codex import fire_codex
from machineconfig.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AI_SPEC, API_SPEC, DEFAULT_SEAPRATOR
from machineconfig.scripts.python.helpers.helpers_agents.reasoning_capabilities import ReasoningEffort


runner = CliRunner()


def _make_codex_ai_spec(*, reasoning_effort: ReasoningEffort | None) -> AI_SPEC:
    return AI_SPEC(
        provider="openai",
        model="gpt-5.4",
        agent="codex",
        machine="local",
        api_spec=API_SPEC(api_key=None, api_name="", api_label="", api_account=""),
        reasoning_effort=reasoning_effort,
    )


def test_parallel_create_help_includes_reasoning_effort_option() -> None:
    result = runner.invoke(agents.get_app(), ["parallel", "create", "--help"])

    assert result.exit_code == 0
    assert "--reasoning-effort" in result.output
    assert "-r" in result.output


def test_parallel_create_passes_reasoning_effort_to_impl() -> None:
    with patch("machineconfig.scripts.python.helpers.helpers_agents.agents_impl.agents_create") as impl:
        result = runner.invoke(
            agents.get_app(),
            [
                "parallel",
                "create",
                "--agent",
                "codex",
                "--prompt",
                "inspect the repo",
                "--context",
                "task one",
                "--reasoning-effort",
                "high",
            ],
        )

    assert result.exit_code == 0
    impl.assert_called_once_with(
        agent="codex",
        host="local",
        model=None,
        reasoning_effort="high",
        provider=None,
        context="task one",
        context_path=None,
        separator=DEFAULT_SEAPRATOR,
        agent_load=3,
        prompt="inspect the repo",
        prompt_path=None,
        job_name="AI_Agents",
        join_prompt_and_context=False,
        output_path=None,
        agents_dir=None,
        interactive=False,
    )


def test_agents_impl_rejects_reasoning_effort_for_non_codex() -> None:
    with pytest.raises(ValueError, match="only supported for --agent codex"):
        agents_impl.agents_create(
            agent="copilot",
            host="local",
            model=None,
            reasoning_effort="high",
            provider=None,
            context="task one",
            context_path=None,
            separator=DEFAULT_SEAPRATOR,
            agent_load=1,
            prompt="inspect the repo",
            prompt_path=None,
            job_name="AI_Agents",
            join_prompt_and_context=False,
            output_path=None,
            agents_dir=None,
            interactive=False,
        )


def test_fire_codex_includes_reasoning_effort_config() -> None:
    repo_root = Path("/workspace/repo")
    prompt_path = repo_root / "prompts" / "agent_0_prompt.txt"

    command = fire_codex(ai_spec=_make_codex_ai_spec(reasoning_effort="high"), prompt_path=prompt_path, repo_root=repo_root)

    assert """-c 'model_reasoning_effort="high"'""" in command


def test_fire_codex_omits_reasoning_effort_config_when_not_requested() -> None:
    repo_root = Path("/workspace/repo")
    prompt_path = repo_root / "prompts" / "agent_0_prompt.txt"

    command = fire_codex(ai_spec=_make_codex_ai_spec(reasoning_effort=None), prompt_path=prompt_path, repo_root=repo_root)

    assert "model_reasoning_effort" not in command


def test_interactive_context_directory_with_multiple_text_files_skips_separator_prompt(tmp_path: Path) -> None:
    context_root = tmp_path / "context"
    context_root.mkdir()
    context_root.joinpath("a.md").write_text("one", encoding="utf-8")
    context_root.joinpath("b.txt").write_text("two", encoding="utf-8")

    assert agent_impl_interactive.separator_is_applicable_for_context_path(context_root) is False


def test_interactive_main_collects_values_and_delegates() -> None:
    collected = agent_impl_interactive.InteractiveAgentCreateParams(
        agent="codex",
        host="docker",
        model="gpt-5.4",
        reasoning_effort="high",
        provider="openai",
        agent_load=5,
        context=None,
        context_path="/tmp/context",
        separator=DEFAULT_SEAPRATOR,
        prompt="inspect the repo",
        prompt_path=None,
        job_name="abc",
        join_prompt_and_context=True,
        output_path="/tmp/layout.json",
        agents_dir="/tmp/agents",
    )

    with (
        patch.object(agent_impl_interactive, "_collect_inputs", return_value=collected) as collect_inputs,
        patch("machineconfig.scripts.python.helpers.helpers_agents.agents_impl.agents_create") as impl,
    ):
        agent_impl_interactive.main(
            agent="copilot",
            host="local",
            model=None,
            reasoning_effort=None,
            provider=None,
            agent_load=3,
            context="existing context",
            context_path=None,
            separator=DEFAULT_SEAPRATOR,
            prompt=None,
            prompt_path="/tmp/prompt.md",
            job_name="AI_Agents",
            join_prompt_and_context=True,
            output_path="/tmp/layout.json",
            agents_dir="/tmp/agents",
        )

    collect_inputs.assert_called_once_with(
        agent="copilot",
        join_prompt_and_context=True,
        output_path="/tmp/layout.json",
        agents_dir="/tmp/agents",
        host="local",
        model=None,
        reasoning_effort=None,
        provider=None,
        agent_load=3,
        context="existing context",
        context_path=None,
        separator=DEFAULT_SEAPRATOR,
        prompt=None,
        prompt_path="/tmp/prompt.md",
    )
    impl.assert_called_once_with(
        agent="codex",
        host="docker",
        model="gpt-5.4",
        reasoning_effort="high",
        provider="openai",
        agent_load=5,
        context=None,
        context_path="/tmp/context",
        separator=DEFAULT_SEAPRATOR,
        prompt="inspect the repo",
        prompt_path=None,
        job_name="abc",
        join_prompt_and_context=True,
        output_path="/tmp/layout.json",
        agents_dir="/tmp/agents",
        interactive=False,
    )


def test_collect_reviewed_create_options_updates_only_selected_values() -> None:
    with (
        patch.object(
            agent_impl_interactive,
            "choose_from_options",
            return_value=[
                "output_path = <leave empty>",
                "provider = <leave empty>",
            ],
        ) as choose_from_options,
        patch.object(
            agent_impl_interactive,
            "_prompt_optional_text_value",
            return_value="/tmp/layout.json",
        ) as prompt_optional_text_value,
        patch.object(
            agent_impl_interactive,
            "_choose_optional_option",
            return_value="openai",
        ) as choose_optional_option,
    ):
        reviewed = agent_impl_interactive._collect_reviewed_create_options(  # pyright: ignore[reportPrivateUsage]
            agent="codex",
            join_prompt_and_context=False,
            output_path=None,
            agents_dir=None,
            host="local",
            reasoning_effort=None,
            provider=None,
        )

    assert reviewed == agent_impl_interactive.InteractiveCreateReviewOptions(
        join_prompt_and_context=False,
        output_path="/tmp/layout.json",
        agents_dir=None,
        host="local",
        reasoning_effort=None,
        provider="openai",
    )
    assert choose_from_options.call_args.kwargs["multi"] is True
    assert choose_from_options.call_args.kwargs["header"] == "Create Options"
    prompt_optional_text_value.assert_called_once_with(label="output path", current=None)
    choose_optional_option.assert_called_once_with(
        options=("openai",),
        current=None,
        msg="Choose provider",
        header="Provider",
    )
