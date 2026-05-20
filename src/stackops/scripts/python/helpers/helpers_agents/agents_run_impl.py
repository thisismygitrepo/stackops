from pathlib import Path
from platform import system
from typing import cast

from stackops.utils.accessories import randstr

from stackops.scripts.python.helpers.helpers_agents.agents_run_context import (
    PROMPTS_WHERE,
    edit_prompts_yaml,
    ensure_prompts_yaml_exists,
    prompts_yaml_format_explanation,
    resolve_context,
    resolve_prompts_yaml_paths,
)
import stackops.scripts.python.helpers.helpers_agents.agents_shell as agent_shell
from stackops.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AGENTS, PROVIDER
from stackops.scripts.python.helpers.helpers_agents.mcp_install import resolve_agent_launch_prefix
from stackops.scripts.python.helpers.helpers_agents.reasoning_capabilities import (
    ReasoningEffort,
    copilot_reasoning_args,
    normalize_reasoning_effort,
)
from stackops.utils.accessories import get_repo_root


def _format_shell_args(values: list[str], *, is_windows: bool) -> str:
    if len(values) == 0:
        return ""
    return " " + " ".join(agent_shell.quote_for_shell(value, is_windows=is_windows) for value in values)


def make_prompt_file(prompt: str, context: str) -> Path:
    prompt_file = Path.home().joinpath("tmp_results", "tmp_files", "agents", f"run_prompt_{randstr()}.md")
    prompt_file.parent.mkdir(parents=True, exist_ok=True)
    payload = f"""# Context
{context}

# Prompt
{prompt}
"""
    prompt_file.write_text(payload, encoding="utf-8")
    return prompt_file


def _print_prompt_file_preview(prompt_file: Path) -> None:
    from rich.console import Console
    from rich.panel import Panel
    from rich.syntax import Syntax

    payload = prompt_file.read_text(encoding="utf-8")
    console = Console()
    console.print(
        Panel(
            Syntax(code=payload, lexer="markdown", word_wrap=True),
            title=f"📄 Prompt file @ {prompt_file}",
            subtitle="Prompt + context sent to agent",
        ),
    )


def _build_codex_reasoning_arg(reasoning_effort: ReasoningEffort | None, is_windows: bool) -> str:
    if reasoning_effort is None:
        return ""
    config_value = agent_shell.quote_for_shell(f'model_reasoning_effort="{reasoning_effort}"', is_windows=is_windows)
    return f" -c {config_value}"


def _build_pi_thinking_arg(reasoning_effort: ReasoningEffort | None, is_windows: bool) -> str:
    if reasoning_effort is None:
        return ""
    if reasoning_effort == "none":
        thinking_level = "off"
    else:
        thinking_level = reasoning_effort
    return f" --thinking {agent_shell.quote_for_shell(thinking_level, is_windows=is_windows)}"


def _build_copilot_reasoning_arg(reasoning_effort: ReasoningEffort | None, is_windows: bool) -> str:
    copilot_reasoning = copilot_reasoning_args(reasoning_effort=reasoning_effort)
    if len(copilot_reasoning) == 0:
        return ""
    return f" {copilot_reasoning[0]} {agent_shell.quote_for_shell(copilot_reasoning[1], is_windows=is_windows)}"


def build_agent_command(
    agent: AGENTS,
    prompt_file: Path,
    reasoning_effort: ReasoningEffort | None,
    *,
    model: str | None = None,
    provider: PROVIDER | None = None,
    is_windows: bool | None = None,
) -> str:
    resolved_is_windows = system() == "Windows" if is_windows is None else is_windows
    prompt_file_q = agent_shell.quote_for_shell(str(prompt_file), is_windows=resolved_is_windows)
    agent_cli = cast(str, agent)
    repo_root = get_repo_root(Path.cwd())
    agent_launch_prefix = resolve_agent_launch_prefix(agent=agent, repo_root=repo_root)
    agent_launch_prefix_q = _format_shell_args(agent_launch_prefix, is_windows=resolved_is_windows)
    normalized_reasoning_effort = normalize_reasoning_effort(agent=agent, reasoning_effort=reasoning_effort)

    if resolved_is_windows:
        prompt_content_expr = f"(Get-Content -Raw {prompt_file_q})"
    else:
        prompt_content_expr = f'"$(cat {prompt_file_q})"'

    match agent:
        case "copilot":
            model_arg = ""
            if model is not None:
                model_arg = f" --model {agent_shell.quote_for_shell(model, is_windows=resolved_is_windows)}"
            reasoning_arg = _build_copilot_reasoning_arg(reasoning_effort=normalized_reasoning_effort, is_windows=resolved_is_windows)
            return f"{agent_cli}{model_arg}{reasoning_arg} -p {prompt_content_expr} --yolo"
        case "codex":
            model_arg = ""
            if model is not None:
                model_arg = f" --model {agent_shell.quote_for_shell(model, is_windows=resolved_is_windows)}"
            reasoning_arg = _build_codex_reasoning_arg(reasoning_effort=normalized_reasoning_effort, is_windows=resolved_is_windows)
            if resolved_is_windows:
                return f"Get-Content -Raw {prompt_file_q} | {agent_cli} exec{model_arg}{reasoning_arg} -"
            return f"{agent_cli} exec{model_arg}{reasoning_arg} - < {prompt_file_q}"
        case "forge":
            return f"{agent_cli} -p {prompt_content_expr}"
        case "crush":
            return f"{agent_cli} run {prompt_file_q}"
        case "claude":
            return f"{agent_cli} -p {prompt_content_expr}"
        case "qwen":
            return f"{agent_cli} --yolo --prompt {prompt_file_q}"
        case "q":
            return f"{agent_cli} chat {prompt_content_expr}"
        case "opencode":
            return f"{agent_cli} run {prompt_content_expr}"
        case "kilocode":
            return f"{agent_cli} {prompt_content_expr}"
        case "cline":
            return f"{agent_cli}{agent_launch_prefix_q} --yolo {prompt_content_expr}"
        case "auggie":
            return f"{agent_cli} --print {prompt_content_expr}"
        case "warp-cli":
            return f"{agent_cli} agent run --prompt {prompt_content_expr}"
        case "droid":
            return f"{agent_cli} exec -f {prompt_file_q}"
        case "pi":
            provider_arg = ""
            if provider is not None:
                provider_arg = f" --provider {agent_shell.quote_for_shell(provider, is_windows=resolved_is_windows)}"
            model_arg = ""
            if model is not None:
                model_arg = f" --model {agent_shell.quote_for_shell(model, is_windows=resolved_is_windows)}"
            thinking_arg = _build_pi_thinking_arg(reasoning_effort=normalized_reasoning_effort, is_windows=resolved_is_windows)
            return f"{agent_cli}{provider_arg}{model_arg}{thinking_arg} -p {prompt_content_expr}"
        case "cursor-agent":
            return f"{agent_cli} -p {prompt_content_expr} --output-format text"


def run(
    prompt: str | None,
    agent: AGENTS,
    reasoning_effort: ReasoningEffort | None,
    context: str | None,
    context_path: str | None,
    prompts_yaml_path: str | None,
    context_name: str | None,
    where: PROMPTS_WHERE,
    edit: bool,
    show_prompts_yaml_format: bool,
) -> None:
    if _should_prepare_prompts_yaml(
        context=context,
        context_path=context_path,
        context_name=context_name,
        edit=edit,
        show_prompts_yaml_format=show_prompts_yaml_format,
    ):
        yaml_locations = resolve_prompts_yaml_paths(prompts_yaml_path=prompts_yaml_path, where=where)
        created_yaml_paths: list[Path] = []
        for location_name, yaml_path in yaml_locations:
            should_create = _should_scaffold_prompts_yaml(location_name=location_name, prompts_yaml_path=prompts_yaml_path, where=where)
            if should_create and ensure_prompts_yaml_exists(yaml_path=yaml_path):
                created_yaml_paths.append(yaml_path)
        if len(created_yaml_paths) > 0:
            import typer

            for created_yaml_path in created_yaml_paths:
                typer.echo(f"Created prompts YAML template at: {created_yaml_path}")
        if edit:
            editable_locations = [(name, path) for name, path in yaml_locations if path.exists() and path.is_file()]
            for _, yaml_path in editable_locations:
                edit_prompts_yaml(yaml_path=yaml_path)
        if show_prompts_yaml_format:
            import typer

            typer.echo(prompts_yaml_format_explanation(yaml_paths=yaml_locations))
    has_explicit_context = context is not None or context_path is not None or context_name is not None
    if (edit or show_prompts_yaml_format) and prompt is None and not has_explicit_context:
        return
    resolved_context = resolve_context(context=context, context_path=context_path, prompts_yaml_path=prompts_yaml_path, context_name=context_name, where=where)
    prompt_text = prompt if prompt is not None else ""
    prompt_file = make_prompt_file(prompt=prompt_text, context=resolved_context)
    _print_prompt_file_preview(prompt_file=prompt_file)
    command_line = build_agent_command(agent=agent, prompt_file=prompt_file, reasoning_effort=reasoning_effort)

    from stackops.utils.code import exit_then_run_shell_script
    exit_then_run_shell_script(script=command_line, strict=False)


def _should_prepare_prompts_yaml(
    *,
    context: str | None,
    context_path: str | None,
    context_name: str | None,
    edit: bool,
    show_prompts_yaml_format: bool,
) -> bool:
    if edit or show_prompts_yaml_format:
        return True
    if context_name is not None:
        return True
    return context is None and context_path is None


def _should_scaffold_prompts_yaml(*, location_name: str, prompts_yaml_path: str | None, where: PROMPTS_WHERE) -> bool:
    if prompts_yaml_path is not None:
        return True
    match where:
        case "all" | "a" | "repo" | "r":
            return location_name == "repo"
        case "private" | "p":
            return location_name == "private"
        case "public" | "b":
            return location_name == "public"
        case "library" | "l" | "custom" | "c":
            return False
