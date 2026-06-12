import pytest

from stackops.scripts.python.helpers.helpers_agents.agents_parallel_run_config import ParallelCreateValues
from stackops.scripts.python.helpers.helpers_agents.agents_parallel_run_impl import (
    _reject_multi_run_collision_overrides,
)


def _empty_values() -> ParallelCreateValues:
    return ParallelCreateValues(
        agent=None,
        model=None,
        reasoning_effort=None,
        provider=None,
        host=None,
        context=None,
        context_path=None,
        separator=None,
        agent_load=None,
        stagger_max=None,
        prompt=None,
        prompt_path=None,
        prompt_name=None,
        job_name=None,
        join_prompt_and_context=None,
        run=None,
        output_path=None,
        agents_dir=None,
        interactive=None,
    )


def test_multi_run_rejects_single_job_name_override() -> None:
    overrides = ParallelCreateValues(
        agent=None,
        model=None,
        reasoning_effort=None,
        provider=None,
        host=None,
        context=None,
        context_path=None,
        separator=None,
        agent_load=None,
        stagger_max=None,
        prompt=None,
        prompt_path=None,
        prompt_name=None,
        job_name="shared",
        join_prompt_and_context=None,
        run=None,
        output_path=None,
        agents_dir=None,
        interactive=None,
    )

    with pytest.raises(ValueError, match="--job-name"):
        _reject_multi_run_collision_overrides(
            selected_entries=(("alpha", _empty_values()), ("beta", _empty_values())),
            overrides=overrides,
        )


def test_multi_run_allows_non_colliding_overrides() -> None:
    overrides = ParallelCreateValues(
        agent="codex",
        model="gpt-test",
        reasoning_effort=None,
        provider=None,
        host=None,
        context=None,
        context_path=None,
        separator=None,
        agent_load=2,
        stagger_max=None,
        prompt=None,
        prompt_path=None,
        prompt_name=None,
        job_name=None,
        join_prompt_and_context=None,
        run=True,
        output_path=None,
        agents_dir=None,
        interactive=None,
    )

    _reject_multi_run_collision_overrides(
        selected_entries=(("alpha", _empty_values()), ("beta", _empty_values())),
        overrides=overrides,
    )
