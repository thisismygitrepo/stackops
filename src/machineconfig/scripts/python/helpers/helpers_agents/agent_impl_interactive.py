import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeAlias, cast, get_args

from machineconfig.scripts.python.helpers.helpers_agents.fire_agents_helper_types import (
    AGENTS,
    DEFAULT_SEAPRATOR,
    HOST,
    PROVIDER,
    ReasoningEffort,
)
from machineconfig.scripts.python.helpers.helpers_agents.reasoning_capabilities import reasoning_support
from machineconfig.utils.accessories import get_repo_root, randstr
from machineconfig.utils.options import choose_from_options


_NONE_LABEL = "<leave empty>"
_KEEP_CURRENT_VALUES_LABEL = "<keep current values>"
_CHANGE_JOB_NAME_LABEL = "change job name"
_CONFIRM_GENERATED_JOB_NAME_PREFIX = "use generated job name: "
_CONTEXT_MODE_TEXT = "enter context text"
_CONTEXT_MODE_PATH = "use context path"
_PROMPT_MODE_TEXT = "enter prompt text"
_PROMPT_MODE_PATH = "use prompt path"

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


def _order_current_first[T: str](options: tuple[T, ...] | list[T], current: T | None) -> list[T]:
    ordered = list(options)
    if current is not None and current in ordered:
        ordered.remove(current)
        ordered.insert(0, current)
    return ordered


def _choose_required_option(*, options: tuple[str, ...] | list[str], msg: str, header: str) -> str:
    selection = choose_from_options(options=list(options), msg=msg, multi=False, custom_input=False, header=header, tv=True)
    if selection is None:
        raise ValueError(f"Selection cancelled for {header.lower()}")
    return selection


def _choose_optional_option(*, options: tuple[str, ...] | list[str], current: str | None, msg: str, header: str) -> str | None:
    labels = list(_order_current_first(options=options, current=current))
    insert_at = 0 if current is None else 1
    labels.insert(insert_at, _NONE_LABEL)
    selection = _choose_required_option(options=labels, msg=msg, header=header)
    if selection == _NONE_LABEL:
        return None
    return selection


def _prompt_text(*, label: str, current: str | None, required: bool, hint: str) -> str | None:
    suffix = f" [{current}]" if current else ""
    while True:
        raw = input(f"{label}{suffix}{hint}: ").strip()
        if raw != "":
            return raw
        if current is not None:
            return current
        if not required:
            return None
        print(f"{label} is required.")


def _prompt_bool(*, label: str, current: bool) -> bool:
    current_label = "true" if current else "false"
    chosen = _choose_required_option(
        options=_order_current_first(options=["true", "false"], current=current_label),
        msg=f"Choose {label}",
        header=label.replace("_", " ").title(),
    )
    return chosen == "true"


def _prompt_optional_text_value(*, label: str, current: str | None) -> str | None:
    shown_current = _NONE_LABEL if current is None else current
    raw = input(f"{label} [{shown_current}] (blank keeps current, type {_NONE_LABEL} to clear): ").strip()
    if raw == "":
        return current
    if raw == _NONE_LABEL:
        return None
    return raw


def _prompt_positive_int(*, label: str, current: int) -> int:
    starting_value = current if current > 0 else 3
    while True:
        raw = input(f"{label} [{starting_value}]: ").strip()
        chosen = raw if raw != "" else str(starting_value)
        try:
            value = int(chosen, 10)
        except ValueError:
            print(f"{label} must be a positive integer.")
            continue
        if value <= 0:
            print(f"{label} must be a positive integer.")
            continue
        return value


def _discover_editor_command() -> list[str] | None:
    configured_editor = os.environ.get("VISUAL") or os.environ.get("EDITOR")
    if configured_editor:
        return shlex.split(configured_editor)
    for candidate in ("nano", "vim", "vi"):
        resolved = shutil.which(candidate)
        if resolved is not None:
            return [resolved]
    return None


def _edit_text(*, label: str, current: str | None) -> str | None:
    editor_command = _discover_editor_command()
    if editor_command is None:
        print(f"Enter {label}. Finish with a line containing only .done")
        lines: list[str] = []
        while True:
            line = input()
            if line == ".done":
                break
            lines.append(line)
        value = "\n".join(lines).strip()
        if value != "":
            return value
        return current
    repo_root = get_repo_root(Path.cwd())
    base_dir = Path("/tmp/machineconfig_agent_impl_interactive") if repo_root is None else repo_root / ".ai" / "tmp_scripts" / "agent_impl_interactive"
    base_dir.mkdir(parents=True, exist_ok=True)
    temp_path = base_dir / f"{label.replace(' ', '_')}_{randstr(length=6, lower=True, upper=False, digits=False, punctuation=False)}.md"
    temp_path.write_text("" if current is None else current, encoding="utf-8")
    try:
        subprocess.run([*editor_command, str(temp_path)], check=False)
        value = temp_path.read_text(encoding="utf-8").strip()
        if value != "":
            return value
        return current
    finally:
        temp_path.unlink(missing_ok=True)


def _prompt_multiline_text(*, label: str, current: str | None, required: bool) -> str | None:
    while True:
        value = _edit_text(label=label, current=current)
        if value is not None and value.strip() != "":
            return value
        if not required:
            return None
        print(f"{label} is required.")


def _prompt_existing_path(*, label: str, current: str | None, must_be_file: bool) -> str:
    suffix = f" [{current}]" if current else ""
    while True:
        raw = input(f"{label}{suffix}: ").strip()
        path_raw = raw if raw != "" else current
        if path_raw is None:
            print(f"{label} is required.")
            continue
        path_obj = Path(path_raw).expanduser().resolve()
        if not path_obj.exists():
            print(f"{label} does not exist: {path_obj}")
            continue
        if must_be_file and not path_obj.is_file():
            print(f"{label} must be a file: {path_obj}")
            continue
        return str(path_obj)


def _decode_separator(raw_separator: str) -> str:
    try:
        return bytes(raw_separator, "utf-8").decode("unicode_escape")
    except UnicodeDecodeError:
        return raw_separator


def _prompt_separator(*, current: str) -> str:
    displayed = current.encode("unicode_escape").decode("ascii")
    raw = input(f"separator [{displayed}] (escape sequences like \\\\n are supported): ").strip()
    if raw == "":
        return current
    return _decode_separator(raw)


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
        return _NONE_LABEL
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


def _collect_reviewed_create_options(
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
                join_prompt_and_context_selected = _prompt_bool(
                    label="join_prompt_and_context",
                    current=join_prompt_and_context_selected,
                )
            case "output_path":
                output_path_selected = _prompt_optional_text_value(label="output path", current=output_path_selected)
            case "agents_dir":
                agents_dir_selected = _prompt_optional_text_value(label="agents dir", current=agents_dir_selected)
            case "host":
                host_selected = cast(
                    HOST,
                    _choose_required_option(
                        options=_order_current_first(cast(tuple[HOST, ...], get_args(HOST)), host_selected),
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
                        _choose_optional_option(
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
                        _choose_optional_option(
                            options=provider_options,
                            current=provider_selected,
                            msg="Choose provider",
                            header="Provider",
                        ),
                    )
                else:
                    provider_selected = cast(
                        PROVIDER,
                        _choose_required_option(
                            options=_order_current_first(provider_options, provider_selected),
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


def separator_is_applicable_for_context_path(context_path: Path) -> bool:
    if context_path.is_file():
        return True
    if not context_path.is_dir():
        return True
    text_files = [item for item in context_path.rglob("*") if item.is_file() and item.suffix.lower() in {".md", ".txt"}]
    return len(text_files) <= 1


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
        _choose_required_option(
        options=_order_current_first(cast(tuple[AGENTS, ...], get_args(AGENTS)), agent),
        msg="Choose agent",
        header="Agent",
        ),
    )
    reviewed_create_options = _collect_reviewed_create_options(
        agent=agent_selected,
        join_prompt_and_context=join_prompt_and_context,
        output_path=output_path,
        agents_dir=agents_dir,
        host=host,
        reasoning_effort=reasoning_effort,
        provider=provider,
    )
    model_selected = _prompt_text(label="model", current=model, required=False, hint=" (blank keeps default)")
    agent_load_selected = _prompt_positive_int(label="agent load", current=agent_load)
    context_mode = _choose_required_option(
        options=[_CONTEXT_MODE_PATH, _CONTEXT_MODE_TEXT] if context_path is not None and context is None else [_CONTEXT_MODE_TEXT, _CONTEXT_MODE_PATH],
        msg="Choose how to provide context",
        header="Context",
    )
    if context_mode == _CONTEXT_MODE_TEXT:
        context_selected = _prompt_multiline_text(label="context", current=context, required=True)
        context_path_selected = None
        separator_selected = _prompt_separator(current=separator)
    else:
        context_selected = None
        context_path_selected = _prompt_existing_path(label="context path", current=context_path, must_be_file=False)
        separator_selected = separator
        if separator_is_applicable_for_context_path(Path(context_path_selected)):
            separator_selected = _prompt_separator(current=separator)
    prompt_mode = _choose_required_option(
        options=[_PROMPT_MODE_PATH, _PROMPT_MODE_TEXT] if prompt_path is not None and prompt is None else [_PROMPT_MODE_TEXT, _PROMPT_MODE_PATH],
        msg="Choose how to provide prompt",
        header="Prompt",
    )
    if prompt_mode == _PROMPT_MODE_TEXT:
        prompt_selected = _prompt_multiline_text(label="prompt", current=prompt, required=True)
        prompt_path_selected = None
    else:
        prompt_selected = None
        prompt_path_selected = _prompt_existing_path(label="prompt path", current=prompt_path, must_be_file=True)
    generated_job_name = randstr(length=3, lower=True, upper=False, digits=False, punctuation=False)
    job_choice = _choose_required_option(
        options=[f"{_CONFIRM_GENERATED_JOB_NAME_PREFIX}{generated_job_name}", _CHANGE_JOB_NAME_LABEL],
        msg="Confirm the generated job name or choose a custom one",
        header="Job Name",
    )
    if job_choice == _CHANGE_JOB_NAME_LABEL:
        job_name_selected = cast(str, _prompt_text(label="job name", current=None, required=True, hint=""))
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
