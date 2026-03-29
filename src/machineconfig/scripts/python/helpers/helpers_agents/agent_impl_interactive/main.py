from dataclasses import dataclass
from pathlib import Path
from typing import cast, get_args

from machineconfig.scripts.python.helpers.helpers_agents.agent_impl_interactive.common import (
    choose_required_option,
    order_current_first,
    prompt_existing_path,
    prompt_multiline_text,
    prompt_positive_int,
    prompt_separator,
    prompt_text,
    separator_is_applicable_for_context_path,
)
from machineconfig.scripts.python.helpers.helpers_agents.agent_impl_interactive.create_options import (
    collect_reviewed_create_options,
)
from machineconfig.scripts.python.helpers.helpers_agents.fire_agents_helper_types import (
    AGENTS,
    DEFAULT_SEAPRATOR,
    HOST,
    PROVIDER,
    ReasoningEffort,
)
from machineconfig.utils.accessories import randstr


_CHANGE_JOB_NAME_LABEL = "change job name"
_CONFIRM_GENERATED_JOB_NAME_PREFIX = "use generated job name: "
_CONTEXT_MODE_TEXT = "enter context text"
_CONTEXT_MODE_PATH = "use context path"
_PROMPT_MODE_TEXT = "enter prompt text"
_PROMPT_MODE_PATH = "use prompt path"


@dataclass(frozen=True, slots=True)
class InteractiveAgentCreateParams:
    agent: AGENTS
    host: HOST
    model: str | None
    reasoning_effort: ReasoningEffort | None
    provider: PROVIDER | None
    agent_load: int
    context: str | None
    context_path: str | None
    separator: str
    prompt: str | None
    prompt_path: str | None
    job_name: str
    join_prompt_and_context: bool
    output_path: str | None
    agents_dir: str | None


def _collect_inputs(
    *,
    agent: AGENTS,
    join_prompt_and_context: bool,
    output_path: str | None,
    agents_dir: str | None,
    host: HOST,
    model: str | None,
    reasoning_effort: ReasoningEffort | None,
    provider: PROVIDER | None,
    agent_load: int,
    context: str | None,
    context_path: str | None,
    separator: str,
    prompt: str | None,
    prompt_path: str | None,
) -> InteractiveAgentCreateParams:
    agent_selected = cast(
        AGENTS,
        choose_required_option(
            options=order_current_first(cast(tuple[AGENTS, ...], get_args(AGENTS)), agent),
            msg="Choose agent",
            header="Agent",
        ),
    )
    reviewed_create_options = collect_reviewed_create_options(
        agent=agent_selected,
        join_prompt_and_context=join_prompt_and_context,
        output_path=output_path,
        agents_dir=agents_dir,
        host=host,
        reasoning_effort=reasoning_effort,
        provider=provider,
    )
    model_selected = prompt_text(label="model", current=model, required=False, hint=" (blank keeps default)")
    agent_load_selected = prompt_positive_int(label="agent load", current=agent_load)
    context_mode = choose_required_option(
        options=[_CONTEXT_MODE_PATH, _CONTEXT_MODE_TEXT] if context_path is not None and context is None else [_CONTEXT_MODE_TEXT, _CONTEXT_MODE_PATH],
        msg="Choose how to provide context",
        header="Context",
    )
    if context_mode == _CONTEXT_MODE_TEXT:
        context_selected = prompt_multiline_text(label="context", current=context, required=True)
        context_path_selected = None
        separator_selected = prompt_separator(current=separator)
    else:
        context_selected = None
        context_path_selected = prompt_existing_path(label="context path", current=context_path, must_be_file=False)
        separator_selected = separator
        if separator_is_applicable_for_context_path(Path(context_path_selected)):
            separator_selected = prompt_separator(current=separator)
    prompt_mode = choose_required_option(
        options=[_PROMPT_MODE_PATH, _PROMPT_MODE_TEXT] if prompt_path is not None and prompt is None else [_PROMPT_MODE_TEXT, _PROMPT_MODE_PATH],
        msg="Choose how to provide prompt",
        header="Prompt",
    )
    if prompt_mode == _PROMPT_MODE_TEXT:
        prompt_selected = prompt_multiline_text(label="prompt", current=prompt, required=True)
        prompt_path_selected = None
    else:
        prompt_selected = None
        prompt_path_selected = prompt_existing_path(label="prompt path", current=prompt_path, must_be_file=True)
    generated_job_name = randstr(length=3, lower=True, upper=False, digits=False, punctuation=False)
    job_choice = choose_required_option(
        options=[f"{_CONFIRM_GENERATED_JOB_NAME_PREFIX}{generated_job_name}", _CHANGE_JOB_NAME_LABEL],
        msg="Confirm the generated job name or choose a custom one",
        header="Job Name",
    )
    if job_choice == _CHANGE_JOB_NAME_LABEL:
        job_name_selected = cast(str, prompt_text(label="job name", current=None, required=True, hint=""))
    else:
        job_name_selected = generated_job_name
    return InteractiveAgentCreateParams(
        agent=agent_selected,
        host=reviewed_create_options.host,
        model=model_selected,
        reasoning_effort=reviewed_create_options.reasoning_effort,
        provider=reviewed_create_options.provider,
        agent_load=agent_load_selected,
        context=context_selected,
        context_path=context_path_selected,
        separator=separator_selected,
        prompt=prompt_selected,
        prompt_path=prompt_path_selected,
        job_name=job_name_selected,
        join_prompt_and_context=reviewed_create_options.join_prompt_and_context,
        output_path=reviewed_create_options.output_path,
        agents_dir=reviewed_create_options.agents_dir,
    )


def main(
    *,
    agent: AGENTS = "copilot",
    host: HOST = "local",
    model: str | None = None,
    reasoning_effort: ReasoningEffort | None = None,
    provider: PROVIDER | None = None,
    agent_load: int = 3,
    context: str | None = None,
    context_path: str | None = None,
    separator: str = DEFAULT_SEAPRATOR,
    prompt: str | None = None,
    prompt_path: str | None = None,
    job_name: str | None = None,
    join_prompt_and_context: bool = False,
    output_path: str | None = None,
    agents_dir: str | None = None,
) -> None:
    _ = job_name
    collected = _collect_inputs(
        agent=agent,
        join_prompt_and_context=join_prompt_and_context,
        output_path=output_path,
        agents_dir=agents_dir,
        host=host,
        model=model,
        reasoning_effort=reasoning_effort,
        provider=provider,
        agent_load=agent_load,
        context=context,
        context_path=context_path,
        separator=separator,
        prompt=prompt,
        prompt_path=prompt_path,
    )
    from machineconfig.scripts.python.helpers.helpers_agents.agents_impl import agents_create

    agents_create(
        agent=collected.agent,
        host=collected.host,
        model=collected.model,
        reasoning_effort=collected.reasoning_effort,
        provider=collected.provider,
        agent_load=collected.agent_load,
        context=collected.context,
        context_path=collected.context_path,
        separator=collected.separator,
        prompt=collected.prompt,
        prompt_path=collected.prompt_path,
        job_name=collected.job_name,
        join_prompt_and_context=collected.join_prompt_and_context,
        output_path=collected.output_path,
        agents_dir=collected.agents_dir,
        interactive=False,
    )
