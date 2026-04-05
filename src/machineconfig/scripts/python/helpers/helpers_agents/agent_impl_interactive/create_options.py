from dataclasses import dataclass
from typing import Final, Literal, TypeAlias, cast, get_args

from machineconfig.scripts.python.helpers.helpers_agents.agent_impl_interactive.common import (
    order_current_first,
    prompt_optional_text_value,
)
from machineconfig.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AGENTS, HOST, PROVIDER, ReasoningEffort
from machineconfig.scripts.python.helpers.helpers_agents.reasoning_capabilities import reasoning_support
from machineconfig.utils.options_utils.textual_options_form_types import (
    OptionValue,
    SelectedOptionMap,
    TextualOptionMap,
    TextualOptionSpec,
    use_textual_options_form,
)


TextFieldDecision: TypeAlias = Literal["keep current", "edit value"]

_KEEP_CURRENT_TEXT_FIELD: Final[TextFieldDecision] = "keep current"
_EDIT_TEXT_FIELD: Final[TextFieldDecision] = "edit value"
_TEXT_FIELD_DECISIONS: Final[tuple[TextFieldDecision, ...]] = (_KEEP_CURRENT_TEXT_FIELD, _EDIT_TEXT_FIELD)

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


@dataclass(frozen=True, slots=True)
class _CreateOptionsFormSelection:
    join_prompt_and_context: bool
    output_path: TextFieldDecision
    agents_dir: TextFieldDecision
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


def _format_output_path_value(value: str | None) -> str:
    if value is None:
        return "auto: layout.json inside agents_dir"
    return value


def _format_agents_dir_value(value: str | None) -> str:
    if value is None:
        return "auto: .ai/agents derived from job_name"
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
    reasoning_effort: ReasoningEffort | None,
    provider: PROVIDER | None,
) -> dict[EditableCreateOption, str]:
    return {
        "join_prompt_and_context": f"join_prompt_and_context = {join_prompt_and_context}",
        "output_path": f"output_path = {_format_output_path_value(output_path)}",
        "agents_dir": f"agents_dir = {_format_agents_dir_value(agents_dir)}",
        "host": f"host = {host}",
        "reasoning_effort": f"reasoning_effort = {_format_reasoning_effort_value(agent=agent, value=reasoning_effort)}",
        "provider": f"provider = {_format_provider_value(agent=agent, value=provider)}",
    }


def _to_option_values[T: str | float | int | bool | None](values: list[T] | tuple[T, ...]) -> list[OptionValue]:
    return [value for value in values]


def _option_spec(*, default: OptionValue, options: list[OptionValue]) -> TextualOptionSpec:
    return {
        "default": default,
        "options": options,
    }


def _build_create_options_form(
    *,
    agent: AGENTS,
    join_prompt_and_context: bool,
    output_path: str | None,
    agents_dir: str | None,
    host: HOST,
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
        reasoning_effort=reasoning_effort,
        provider=provider,
    )
    return {
        review_options["join_prompt_and_context"]: _option_spec(
            default=join_prompt_and_context,
            options=_to_option_values([join_prompt_and_context, not join_prompt_and_context]),
        ),
        review_options["output_path"]: _option_spec(
            default=_KEEP_CURRENT_TEXT_FIELD,
            options=_to_option_values(_TEXT_FIELD_DECISIONS),
        ),
        review_options["agents_dir"]: _option_spec(
            default=_KEEP_CURRENT_TEXT_FIELD,
            options=_to_option_values(_TEXT_FIELD_DECISIONS),
        ),
        review_options["host"]: _option_spec(
            default=host,
            options=_to_option_values(order_current_first(options=cast(tuple[HOST, ...], get_args(HOST)), current=host)),
        ),
        review_options["reasoning_effort"]: _option_spec(
            default=reasoning_effort,
            options=reasoning_options,
        ),
        review_options["provider"]: _option_spec(
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


def _require_text_field_decision(*, selected_values: SelectedOptionMap, key: str) -> TextFieldDecision:
    value = _require_selected_value(selected_values=selected_values, key=key)
    if isinstance(value, str) and value in _TEXT_FIELD_DECISIONS:
        return value
    raise TypeError(f"""Expected "{key}" to be one of {_TEXT_FIELD_DECISIONS}, got {value!r}.""")


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
    reasoning_effort: ReasoningEffort | None,
    provider: PROVIDER | None,
) -> _CreateOptionsFormSelection:
    review_options = _build_review_option_labels(
        agent=agent,
        join_prompt_and_context=join_prompt_and_context,
        output_path=output_path,
        agents_dir=agents_dir,
        host=host,
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
                reasoning_effort=reasoning_effort,
                provider=provider,
            )
        )
    except RuntimeError as exc:
        raise ValueError("Selection cancelled for create options") from exc
    return _CreateOptionsFormSelection(
        join_prompt_and_context=_require_bool_value(selected_values=selected_values, key=review_options["join_prompt_and_context"]),
        output_path=_require_text_field_decision(selected_values=selected_values, key=review_options["output_path"]),
        agents_dir=_require_text_field_decision(selected_values=selected_values, key=review_options["agents_dir"]),
        host=_require_choice(selected_values=selected_values, key=review_options["host"], options=cast(tuple[HOST, ...], get_args(HOST))),
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
        reasoning_effort=reasoning_current,
        provider=provider_current,
    )

    output_path_selected = output_path
    agents_dir_selected = agents_dir
    if selection.output_path == _EDIT_TEXT_FIELD:
        output_path_selected = prompt_optional_text_value(label="output path", current=output_path_selected)
    if selection.agents_dir == _EDIT_TEXT_FIELD:
        agents_dir_selected = prompt_optional_text_value(label="agents dir", current=agents_dir_selected)

    return InteractiveCreateReviewOptions(
        join_prompt_and_context=selection.join_prompt_and_context,
        output_path=output_path_selected,
        agents_dir=agents_dir_selected,
        host=selection.host,
        reasoning_effort=selection.reasoning_effort,
        provider=selection.provider,
    )
