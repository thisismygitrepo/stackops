import pytest

from stackops.scripts.python.helpers.helpers_agents import agents_parallel_run_impl
from stackops.scripts.python.helpers.helpers_agents.agents_parallel_run_config import ResolvedParallelCreateValues


def _resolved_values_without_context() -> ResolvedParallelCreateValues:
    return ResolvedParallelCreateValues(
        agent="codex",
        model=None,
        reasoning_effort=None,
        provider=None,
        host="local",
        context=None,
        context_path=None,
        separator="\n@-@\n",
        agent_load=10,
        prompt="prompt",
        prompt_path=None,
        prompt_name=None,
        job_name="updateDocs",
        join_prompt_and_context=False,
        output_path=None,
        agents_dir=None,
        interactive=False,
    )


def test_require_explicit_parallel_context_rejects_missing_context() -> None:
    with pytest.raises(ValueError, match="Parallel run 'update-docs' does not define context or context_path"):
        agents_parallel_run_impl._require_explicit_parallel_context(
            selected_name="update-docs",
            resolved=_resolved_values_without_context(),
        )


def test_require_explicit_parallel_context_accepts_context_path() -> None:
    resolved = _resolved_values_without_context()
    resolved_with_context_path = ResolvedParallelCreateValues(
        agent=resolved.agent,
        model=resolved.model,
        reasoning_effort=resolved.reasoning_effort,
        provider=resolved.provider,
        host=resolved.host,
        context=resolved.context,
        context_path="./context.md",
        separator=resolved.separator,
        agent_load=resolved.agent_load,
        prompt=resolved.prompt,
        prompt_path=resolved.prompt_path,
        prompt_name=resolved.prompt_name,
        job_name=resolved.job_name,
        join_prompt_and_context=resolved.join_prompt_and_context,
        output_path=resolved.output_path,
        agents_dir=resolved.agents_dir,
        interactive=resolved.interactive,
    )

    agents_parallel_run_impl._require_explicit_parallel_context(
        selected_name="update-docs",
        resolved=resolved_with_context_path,
    )
