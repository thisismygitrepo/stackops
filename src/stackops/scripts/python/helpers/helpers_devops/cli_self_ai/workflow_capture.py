from collections.abc import Callable
from typing import Protocol

from stackops.scripts.python.helpers.helpers_agents.agents_parallel_run_config import ParallelCreateValues
from stackops.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AGENTS, HOST, PROVIDER
from stackops.scripts.python.helpers.helpers_agents.reasoning_capabilities import ReasoningEffort


class AgentsCreateImpl(Protocol):
    def __call__(
        self,
        agent: AGENTS,
        model: str | None,
        agent_load: int,
        context: str | None,
        context_path: str | None,
        separator: str,
        prompt: str | None,
        prompt_path: str | None,
        prompt_name: str | None,
        job_name: str | None,
        join_prompt_and_context: bool,
        output_path: str | None,
        agents_dir: str | None,
        host: HOST,
        reasoning_effort: ReasoningEffort | None,
        provider: PROVIDER | None,
        interactive: bool,
    ) -> None: ...


class WorkflowModule(Protocol):
    agents_create_impl: AgentsCreateImpl


def capture_agents_create_values(*, workflow_module: WorkflowModule, workflow_function: Callable[[], None]) -> ParallelCreateValues:
    captured_values: ParallelCreateValues | None = None

    def capture_agents_create(
        agent: AGENTS,
        model: str | None,
        agent_load: int,
        context: str | None,
        context_path: str | None,
        separator: str,
        prompt: str | None,
        prompt_path: str | None,
        prompt_name: str | None,
        job_name: str | None,
        join_prompt_and_context: bool,
        output_path: str | None,
        agents_dir: str | None,
        host: HOST,
        reasoning_effort: ReasoningEffort | None,
        provider: PROVIDER | None,
        interactive: bool,
    ) -> None:
        nonlocal captured_values
        captured_values = ParallelCreateValues(
            agent=agent,
            model=model,
            reasoning_effort=reasoning_effort,
            provider=provider,
            host=host,
            context=context,
            context_path=context_path,
            separator=separator,
            agent_load=agent_load,
            prompt=prompt,
            prompt_path=prompt_path,
            prompt_name=prompt_name,
            job_name=job_name,
            join_prompt_and_context=join_prompt_and_context,
            output_path=output_path,
            agents_dir=agents_dir,
            interactive=interactive,
        )

    original_agents_create_impl = workflow_module.agents_create_impl
    workflow_module.agents_create_impl = capture_agents_create
    try:
        workflow_function()
    finally:
        workflow_module.agents_create_impl = original_agents_create_impl

    if captured_values is None:
        raise RuntimeError("Workflow did not call agents_create_impl")
    return captured_values
