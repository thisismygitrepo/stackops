from dataclasses import dataclass
from typing import Literal, TypeAlias, cast, get_args

from machineconfig.scripts.python.helpers.helpers_agents.agent_impl_interactive.common import (
    NONE_LABEL,
    choose_optional_option,
    choose_required_option,
    order_current_first,
    prompt_bool,
    prompt_optional_text_value,
)
from machineconfig.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AGENTS, HOST, PROVIDER, ReasoningEffort
from machineconfig.scripts.python.helpers.helpers_agents.reasoning_capabilities import reasoning_support
from machineconfig.utils.options import choose_from_options


_KEEP_CURRENT_VALUES_LABEL = "<keep current values>"

EditableCreateOption: TypeAlias = Literal[
    "join_prompt_and_context",
    "output_path",
    "agents_dir",
    "host",
    "reasoning_effort",
    "provider",
]


@dataclass(frozen=True, slots=True)
class InteractiveCreateReviewOptions:
    join_prompt_and_context: bool
    output_path: str | None
    agents_dir: str | None
    host: HOST
    reasoning_effort: ReasoningEffort | None
    provider: PROVIDER | None


def _provider_options_for_agent(agent: AGENTS) -> tuple[PROVIDER, ...]:
    provider_options = cast(tuple[PROVIDER, ...], get_args(PROVIDER))
    match agent:
        case "codex":
            return ("openai",)
        case "gemini":
            return ("google",)
        case _:
            return provider_options


def _provider_allows_none(agent: AGENTS) -> bool:
    return agent not in {"gemini", "crush"}


def _format_nullable_value(value: str | None) -> str:
    if value is None:
        return NONE_LABEL
    return value


def _format_bool_value(value: bool) -> str:
    return "true" if value else "false"


def _build_review_option_labels(
    *,
    join_prompt_and_context: bool,
    output_path: str | None,
    agents_dir: str | None,
    host: HOST,
    reasoning_effort: ReasoningEffort | None,
    provider: PROVIDER | None,
) -> dict[EditableCreateOption, str]:
    return {
        "join_prompt_and_context": f"join_prompt_and_context = {_format_bool_value(join_prompt_and_context)}",
        "output_path": f"output_path = {_format_nullable_value(output_path)}",
        "agents_dir": f"agents_dir = {_format_nullable_value(agents_dir)}",
        "host": f"host = {host}",
        "reasoning_effort": f"reasoning_effort = {_format_nullable_value(reasoning_effort)}",
        "provider": f"provider = {_format_nullable_value(provider)}",
    }


def _choose_create_options_to_edit(
    *,
    join_prompt_and_context: bool,
    output_path: str | None,
    agents_dir: str | None,
    host: HOST,
    reasoning_effort: ReasoningEffort | None,
    provider: PROVIDER | None,
) -> list[EditableCreateOption]:
    review_options = _build_review_option_labels(
        join_prompt_and_context=join_prompt_and_context,
        output_path=output_path,
        agents_dir=agents_dir,
        host=host,
        reasoning_effort=reasoning_effort,
        provider=provider,
    )
    labels = [_KEEP_CURRENT_VALUES_LABEL, *review_options.values()]
    option_by_label: dict[str, EditableCreateOption] = {label: key for key, label in review_options.items()}
    while True:
        selection = choose_from_options(
            options=labels,
            msg="Review current values. Multi-select anything you want to change.",
            multi=True,
            header="Create Options",
            tv=True,
        )
        if selection is None:
            raise ValueError("Selection cancelled for create options")
        if _KEEP_CURRENT_VALUES_LABEL in selection:
            if len(selection) == 1:
                return []
            print(f"Select either {_KEEP_CURRENT_VALUES_LABEL} or specific options to change.")
            continue
        return [option_by_label[label] for label in selection]


def collect_reviewed_create_options(
    *,
    agent: AGENTS,
    join_prompt_and_context: bool,
    output_path: str | None,
    agents_dir: str | None,
    host: HOST,
    reasoning_effort: ReasoningEffort | None,
    provider: PROVIDER | None,
) -> InteractiveCreateReviewOptions:
    support = reasoning_support(agent=agent)
    reasoning_current = reasoning_effort if reasoning_effort in support.efforts else None
    provider_options = _provider_options_for_agent(agent)
    provider_current = provider if provider in provider_options else None
    selected_options = _choose_create_options_to_edit(
        join_prompt_and_context=join_prompt_and_context,
        output_path=output_path,
        agents_dir=agents_dir,
        host=host,
        reasoning_effort=reasoning_current,
        provider=provider_current,
    )

    join_prompt_and_context_selected = join_prompt_and_context
    output_path_selected = output_path
    agents_dir_selected = agents_dir
    host_selected = host
    reasoning_selected = reasoning_current
    provider_selected = provider_current

    for option_name in selected_options:
        match option_name:
            case "join_prompt_and_context":
                join_prompt_and_context_selected = prompt_bool(
                    label="join_prompt_and_context",
                    current=join_prompt_and_context_selected,
                )
            case "output_path":
                output_path_selected = prompt_optional_text_value(label="output path", current=output_path_selected)
            case "agents_dir":
                agents_dir_selected = prompt_optional_text_value(label="agents dir", current=agents_dir_selected)
            case "host":
                host_selected = cast(
                    HOST,
                    choose_required_option(
                        options=order_current_first(cast(tuple[HOST, ...], get_args(HOST)), host_selected),
                        msg="Choose host",
                        header="Host",
                    ),
                )
            case "reasoning_effort":
                if len(support.efforts) == 0:
                    print(f"Reasoning effort is not supported for agent {agent}. Leaving it empty.")
                    reasoning_selected = None
                else:
                    msg = "Choose reasoning effort" if support.note is None else f"Choose reasoning effort. {support.note}"
                    reasoning_selected = cast(
                        ReasoningEffort | None,
                        choose_optional_option(
                            options=support.efforts,
                            current=reasoning_selected,
                            msg=msg,
                            header="Reasoning Effort",
                        ),
                    )
            case "provider":
                if _provider_allows_none(agent=agent):
                    provider_selected = cast(
                        PROVIDER | None,
                        choose_optional_option(
                            options=provider_options,
                            current=provider_selected,
                            msg="Choose provider",
                            header="Provider",
                        ),
                    )
                else:
                    provider_selected = cast(
                        PROVIDER,
                        choose_required_option(
                            options=order_current_first(provider_options, provider_selected),
                            msg="Choose provider",
                            header="Provider",
                        ),
                    )

    return InteractiveCreateReviewOptions(
        join_prompt_and_context=join_prompt_and_context_selected,
        output_path=output_path_selected,
        agents_dir=agents_dir_selected,
        host=host_selected,
        reasoning_effort=reasoning_selected,
        provider=provider_selected,
    )
