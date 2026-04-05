from dataclasses import dataclass
from typing import Literal, TypeAlias, cast, get_args

from machineconfig.scripts.python.helpers.helpers_agents.agent_impl_interactive.common import (
    order_current_first,
)
from machineconfig.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AGENTS, HOST, PROVIDER, ReasoningEffort
from machineconfig.scripts.python.helpers.helpers_agents.reasoning_capabilities import reasoning_support
from machineconfig.utils.options_utils.textual_options_form_types import (
    OptionValue,
    SelectedOptionMap,
    TextualOptionMap,
    TextualSelectOptionSpec,
    TextualTextOptionSpec,
    use_textual_options_form,
)

EditableCreateOption: TypeAlias = Literal[
    "join_prompt_and_context",
    "output_path",
    "agents_dir",
    "host",
    "model",
    "agent_load",
    "job_name",
    "reasoning_effort",
    "provider",
]


@dataclass(frozen=True, slots=True)
class InteractiveCreateReviewOptions:
    join_prompt_and_context: bool
    output_path: str | None
    agents_dir: str | None
    host: HOST
    model: str | None
    agent_load: int
    job_name: str
    reasoning_effort: ReasoningEffort | None
    provider: PROVIDER | None


@dataclass(frozen=True, slots=True)
class _CreateOptionsFormSelection:
    join_prompt_and_context: bool
    output_path: str | None
    agents_dir: str | None
    host: HOST
    model: str | None
    agent_load: int
    job_name: str
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


def _format_output_path_value(value: str | None) -> str:
    if value is None:
        return "auto: layout.json inside agents_dir"
    return value


def _format_agents_dir_value(value: str | None) -> str:
    if value is None:
        return "auto: .ai/agents derived from job_name"
    return value


def _format_model_value(value: str | None) -> str:
    if value is None:
        return "agent default"
    return value


def _format_agent_load_value(value: int) -> str:
    return str(value)


def _format_job_name_value(value: str) -> str:
    return value


def _format_reasoning_effort_value(*, agent: AGENTS, value: ReasoningEffort | None) -> str:
    if value is not None:
        return value
    if len(reasoning_support(agent=agent).efforts) == 0:
        return "not used by this agent"
    return "agent default"


def _format_provider_value(*, agent: AGENTS, value: PROVIDER | None) -> str:
    if value is not None:
        return value
    match agent:
        case "codex":
            return "auto: openai"
        case "gemini":
            return "auto: google"
        case "crush":
            return "required"
        case _:
            return "not passed"


def _build_review_option_labels(
    *,
    agent: AGENTS,
    join_prompt_and_context: bool,
    output_path: str | None,
    agents_dir: str | None,
    host: HOST,
    model: str | None,
    agent_load: int,
    job_name: str,
    reasoning_effort: ReasoningEffort | None,
    provider: PROVIDER | None,
) -> dict[EditableCreateOption, str]:
    return {
        "join_prompt_and_context": f"join_prompt_and_context = {join_prompt_and_context}",
        "output_path": f"output_path = {_format_output_path_value(output_path)}",
        "agents_dir": f"agents_dir = {_format_agents_dir_value(agents_dir)}",
        "host": f"host = {host}",
        "model": f"model = {_format_model_value(model)}",
        "agent_load": f"agent_load = {_format_agent_load_value(agent_load)}",
        "job_name": f"job_name = {_format_job_name_value(job_name)}",
        "reasoning_effort": f"reasoning_effort = {_format_reasoning_effort_value(agent=agent, value=reasoning_effort)}",
        "provider": f"provider = {_format_provider_value(agent=agent, value=provider)}",
    }


def _to_option_values[T: str | float | int | bool | None](values: list[T] | tuple[T, ...]) -> list[OptionValue]:
    return [value for value in values]


def _select_option_spec(*, default: OptionValue, options: list[OptionValue]) -> TextualSelectOptionSpec:
    return {
        "kind": "select",
        "default": default,
        "options": options,
    }


def _text_option_spec(*, default: str | None, allow_blank: bool, placeholder: str) -> TextualTextOptionSpec:
    return {
        "kind": "text",
        "default": default,
        "allow_blank": allow_blank,
        "placeholder": placeholder,
    }


def _build_create_options_form(
    *,
    agent: AGENTS,
    join_prompt_and_context: bool,
    output_path: str | None,
    agents_dir: str | None,
    host: HOST,
    model: str | None,
    agent_load: int,
    job_name: str,
    reasoning_effort: ReasoningEffort | None,
    provider: PROVIDER | None,
) -> TextualOptionMap:
    support = reasoning_support(agent=agent)
    provider_options = _provider_options_for_agent(agent)
    reasoning_options = _to_option_values([None, *order_current_first(options=support.efforts, current=reasoning_effort)])
    provider_form_options: list[OptionValue]
    ordered_provider_options = order_current_first(options=provider_options, current=provider)
    if _provider_allows_none(agent=agent):
        provider_form_options = _to_option_values([None, *ordered_provider_options])
    else:
        provider_form_options = _to_option_values(ordered_provider_options)
    review_options = _build_review_option_labels(
        agent=agent,
        join_prompt_and_context=join_prompt_and_context,
        output_path=output_path,
        agents_dir=agents_dir,
        host=host,
        model=model,
        agent_load=agent_load,
        job_name=job_name,
        reasoning_effort=reasoning_effort,
        provider=provider,
    )
    return {
        review_options["join_prompt_and_context"]: _select_option_spec(
            default=join_prompt_and_context,
            options=_to_option_values([join_prompt_and_context, not join_prompt_and_context]),
        ),
        review_options["output_path"]: _text_option_spec(
            default=output_path,
            allow_blank=True,
            placeholder="Leave blank to auto-create layout.json inside agents_dir",
        ),
        review_options["agents_dir"]: _text_option_spec(
            default=agents_dir,
            allow_blank=True,
            placeholder="Leave blank to derive .ai/agents from job_name",
        ),
        review_options["host"]: _select_option_spec(
            default=host,
            options=_to_option_values(order_current_first(options=cast(tuple[HOST, ...], get_args(HOST)), current=host)),
        ),
        review_options["model"]: _text_option_spec(
            default=model,
            allow_blank=True,
            placeholder="Leave blank to use the agent default model",
        ),
        review_options["agent_load"]: _text_option_spec(
            default=str(agent_load),
            allow_blank=False,
            placeholder="Enter a positive integer",
        ),
        review_options["job_name"]: _text_option_spec(
            default=job_name,
            allow_blank=False,
            placeholder="Enter the job name",
        ),
        review_options["reasoning_effort"]: _select_option_spec(
            default=reasoning_effort,
            options=reasoning_options,
        ),
        review_options["provider"]: _select_option_spec(
            default=provider,
            options=provider_form_options,
        ),
    }


def _require_selected_value(*, selected_values: SelectedOptionMap, key: str) -> object:
    if key not in selected_values:
        raise KeyError(f"""Missing value for "{key}".""")
    return selected_values[key]


def _require_bool_value(*, selected_values: SelectedOptionMap, key: str) -> bool:
    value = _require_selected_value(selected_values=selected_values, key=key)
    if type(value) is not bool:
        raise TypeError(f"""Expected "{key}" to be bool, got {value!r}.""")
    return value


def _require_optional_text_value(*, selected_values: SelectedOptionMap, key: str) -> str | None:
    value = _require_selected_value(selected_values=selected_values, key=key)
    if value is None or isinstance(value, str):
        return value
    raise TypeError(f"""Expected "{key}" to be str | None, got {value!r}.""")


def _require_positive_int_value(*, selected_values: SelectedOptionMap, key: str) -> int:
    value = _require_selected_value(selected_values=selected_values, key=key)
    if not isinstance(value, str):
        raise TypeError(f"""Expected "{key}" to be str, got {value!r}.""")
    try:
        parsed = int(value)
    except ValueError as exc:
        raise TypeError(f"""Expected "{key}" to be a positive integer, got {value!r}.""") from exc
    if parsed <= 0:
        raise TypeError(f"""Expected "{key}" to be a positive integer, got {value!r}.""")
    return parsed


def _require_non_blank_text_value(*, selected_values: SelectedOptionMap, key: str) -> str:
    value = _require_selected_value(selected_values=selected_values, key=key)
    if not isinstance(value, str):
        raise TypeError(f"""Expected "{key}" to be str, got {value!r}.""")
    if len(value.strip()) == 0:
        raise TypeError(f"""Expected "{key}" to be non-blank, got {value!r}.""")
    return value


def _require_choice[T: str](*, selected_values: SelectedOptionMap, key: str, options: tuple[T, ...]) -> T:
    value = _require_selected_value(selected_values=selected_values, key=key)
    if isinstance(value, str) and value in options:
        return cast(T, value)
    raise TypeError(f"""Expected "{key}" to be one of {options}, got {value!r}.""")


def _require_optional_choice[T: str](*, selected_values: SelectedOptionMap, key: str, options: tuple[T, ...]) -> T | None:
    value = _require_selected_value(selected_values=selected_values, key=key)
    if value is None:
        return None
    if isinstance(value, str) and value in options:
        return cast(T, value)
    raise TypeError(f"""Expected "{key}" to be one of {options} or None, got {value!r}.""")


def _collect_create_options_form_selection(
    *,
    agent: AGENTS,
    join_prompt_and_context: bool,
    output_path: str | None,
    agents_dir: str | None,
    host: HOST,
    model: str | None,
    agent_load: int,
    job_name: str,
    reasoning_effort: ReasoningEffort | None,
    provider: PROVIDER | None,
) -> _CreateOptionsFormSelection:
    review_options = _build_review_option_labels(
        agent=agent,
        join_prompt_and_context=join_prompt_and_context,
        output_path=output_path,
        agents_dir=agents_dir,
        host=host,
        model=model,
        agent_load=agent_load,
        job_name=job_name,
        reasoning_effort=reasoning_effort,
        provider=provider,
    )
    provider_options = _provider_options_for_agent(agent)
    try:
        selected_values = use_textual_options_form(
            options=_build_create_options_form(
                agent=agent,
                join_prompt_and_context=join_prompt_and_context,
                output_path=output_path,
                agents_dir=agents_dir,
                host=host,
                model=model,
                agent_load=agent_load,
                job_name=job_name,
                reasoning_effort=reasoning_effort,
                provider=provider,
            )
        )
    except RuntimeError as exc:
        raise ValueError("Selection cancelled for create options") from exc
    return _CreateOptionsFormSelection(
        join_prompt_and_context=_require_bool_value(selected_values=selected_values, key=review_options["join_prompt_and_context"]),
        output_path=_require_optional_text_value(selected_values=selected_values, key=review_options["output_path"]),
        agents_dir=_require_optional_text_value(selected_values=selected_values, key=review_options["agents_dir"]),
        host=_require_choice(selected_values=selected_values, key=review_options["host"], options=cast(tuple[HOST, ...], get_args(HOST))),
        model=_require_optional_text_value(selected_values=selected_values, key=review_options["model"]),
        agent_load=_require_positive_int_value(selected_values=selected_values, key=review_options["agent_load"]),
        job_name=_require_non_blank_text_value(selected_values=selected_values, key=review_options["job_name"]),
        reasoning_effort=_require_optional_choice(selected_values=selected_values, key=review_options["reasoning_effort"], options=reasoning_support(agent=agent).efforts),
        provider=_require_optional_choice(selected_values=selected_values, key=review_options["provider"], options=provider_options),
    )


def collect_reviewed_create_options(
    *,
    agent: AGENTS,
    join_prompt_and_context: bool,
    output_path: str | None,
    agents_dir: str | None,
    host: HOST,
    model: str | None,
    agent_load: int,
    job_name: str,
    reasoning_effort: ReasoningEffort | None,
    provider: PROVIDER | None,
) -> InteractiveCreateReviewOptions:
    support = reasoning_support(agent=agent)
    reasoning_current = reasoning_effort if reasoning_effort in support.efforts else None
    provider_options = _provider_options_for_agent(agent)
    provider_current = provider if provider in provider_options else None
    selection = _collect_create_options_form_selection(
        agent=agent,
        join_prompt_and_context=join_prompt_and_context,
        output_path=output_path,
        agents_dir=agents_dir,
        host=host,
        model=model,
        agent_load=agent_load,
        job_name=job_name,
        reasoning_effort=reasoning_current,
        provider=provider_current,
    )

    return InteractiveCreateReviewOptions(
        join_prompt_and_context=selection.join_prompt_and_context,
        output_path=selection.output_path,
        agents_dir=selection.agents_dir,
        host=selection.host,
        model=selection.model,
        agent_load=selection.agent_load,
        job_name=selection.job_name,
        reasoning_effort=selection.reasoning_effort,
        provider=selection.provider,
    )
