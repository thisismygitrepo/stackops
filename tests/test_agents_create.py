from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from machineconfig.scripts.python import agents
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
