"""Command handlers for the parallel agent workflow."""

from pathlib import Path
from typing import Annotated, get_args

import typer

from stackops.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AGENTS, DEFAULT_SEAPRATOR, HOST, PROVIDER
from stackops.scripts.python.helpers.helpers_agents.reasoning_capabilities import ReasoningEffort


def agents_create(
    agent: Annotated[AGENTS, typer.Option(..., "--agent", "-a", help="Agent type.")] = "codex",
    model: Annotated[str | None, typer.Option(..., "--model", "-m", help="Model to use, agent will use its default otherwise.")] = None,
    reasoning_effort: Annotated[
        ReasoningEffort | None,
        typer.Option(
            ...,
            "--reasoning",
            "-r",
            help="Reasoning effort for codex, copilot, and pi agents. Unsupported agents ignore it and use their default.",
        ),
    ] = None,
    provider: Annotated[PROVIDER | None, typer.Option(..., "--provider", "-v", help="Provider to use (if agent support many)")] = None,
    host: Annotated[HOST, typer.Option(..., "--host", "-h", help=f"Machine to run agents on. One of {', '.join(get_args(HOST))}")] = "local",
    context: Annotated[
        str | None, typer.Option(..., "--context", "-c", help="Context as a direct string. Mutually exclusive with --context-path.")
    ] = None,
    context_path: Annotated[
        str | None, typer.Option(..., "--context-path", "-C", help="Path to the context file/folder, defaults to .ai/todo/")
    ] = None,
    separator: Annotated[str, typer.Option(..., "--separator", "-s", help="Separator for context. Supports escaped values like '\\n'.")] = DEFAULT_SEAPRATOR,
    agent_load: Annotated[int, typer.Option(..., "--agent-load", "-l", min=1, help="Number of tasks per prompt")] = 3,
    prompt: Annotated[str | None, typer.Option(..., "--prompt", "-p", help="Prompt prefix as string")] = None,
    prompt_path: Annotated[str | None, typer.Option(..., "--prompt-path", "-P", help="Path to prompt file")] = None,
    prompt_name: Annotated[str | None, typer.Option(..., "--prompt-name", "-N", help="Prompt entry name from prompts YAML")] = None,
    job_name: Annotated[
        str,
        typer.Option(
            ...,
            "--job-name",
            "-n",
            help="Job label. Also used as the generated layout name and to build the default output directory when --agents-dir is omitted.",
        ),
    ] = "AI_Agents",
    join_prompt_and_context: Annotated[bool, typer.Option(..., "--joined-prompt-context", "-j", help="Join prompt file to the context.")] = False,
    output_path: Annotated[str | None, typer.Option(..., "--output-path", "-o", help="Path to write the layout.json file")] = None,
    agents_dir: Annotated[
        str | None,
        typer.Option(
            ..., "--agents-dir", "-d", help="Exact directory to store agent files in. If not provided, it is built as .ai/agents/<job-name>."
        ),
    ] = None,
    interactive: Annotated[bool, typer.Option(..., "--interactive", "-i", help="Whether to run in interactive mode, asking for missing parameters.")] = False,
) -> None:
    """Create agents layout file, ready to run."""
    from stackops.scripts.python.helpers.helpers_agents.agents_impl import agents_create as impl

    try:
        normalized_separator = _decode_separator(separator=separator)
        impl(
            agent=agent,
            host=host,
            model=model,
            reasoning_effort=reasoning_effort,
            provider=provider,
            context=context,
            context_path=context_path,
            separator=normalized_separator,
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
    except ValueError as e:
        raise typer.BadParameter(str(e)) from e
    except RuntimeError as e:
        typer.echo(str(e))
        raise typer.Exit(1) from e


def collect(
    agent_dir: Annotated[str, typer.Argument(..., help="Path to the agent directory containing the prompts folder")],
    output_path: Annotated[str, typer.Argument(..., help="Path to write the concatenated material files")],
    separator: Annotated[
        str,
        typer.Option(..., help="Separator to use when concatenating material files. Supports escaped values like '\\n'."),
    ] = "\n",
    pattern: Annotated[str | None, typer.Option(..., help="Pattern to match material files (e.g., 'res.txt')")] = None,
) -> None:
    """Collect all material files from an agent directory and concatenate them."""
    from stackops.scripts.python.helpers.helpers_agents.agents_impl import collect as impl

    try:
        normalized_separator = _decode_separator(separator=separator)
        impl(agent_dir=agent_dir, output_path=output_path, separator=normalized_separator, pattern=pattern)
    except ValueError as e:
        raise typer.BadParameter(str(e)) from e


def make_agents_command_template() -> None:
    """Create a template for fire agents."""
    from stackops.scripts.python.helpers.helpers_agents.agents_impl import make_agents_command_template as impl

    try:
        impl()
    except ValueError as e:
        raise typer.BadParameter(str(e)) from e
    except RuntimeError as e:
        typer.echo(str(e))
        raise typer.Exit(1) from e


def _decode_separator(separator: str) -> str:
    try:
        return bytes(separator, "utf-8").decode("unicode_escape")
    except UnicodeDecodeError:
        return separator


def create_context(
    prompt: Annotated[str, typer.Argument(help="Prompt text to send to the selected agent.")],
    job_name: Annotated[str, typer.Option(..., "--job-name", "-n", help="Job name used in ./.ai/agents/<jobName>/context.md output path.")],
    agent: Annotated[AGENTS, typer.Option(..., "--agent", "-a", help="Agent to launch.")] = "copilot",
    separator: Annotated[
        str, typer.Option(..., "--separator", "-s", help="Separator between individual results in context.md. Supports escaped values like '\\n'.")
    ] = DEFAULT_SEAPRATOR,
) -> None:
    """Run one prompt and ask the selected agent to persist a context file for the job."""
    from stackops.scripts.python.helpers.helpers_agents.agents_run_impl import run as impl

    normalized_separator = _decode_separator(separator=separator)
    separator_for_prompt = normalized_separator.encode("unicode_escape").decode("ascii")
    appended_instruction = (
        f"Please store the results in ./.ai/agents/{job_name}/context.md (overwrite) and "
        f'within that file make sure to use "{separator_for_prompt}" to separate the individual results.'
    )
    full_prompt = f"{prompt}\n\n{appended_instruction}"

    try:
        impl(
            prompt=full_prompt,
            agent=agent,
            reasoning_effort=None,
            context="",
            context_path=None,
            prompts_yaml_path=None,
            context_name=None,
            where="all",
            edit=False,
            show_prompts_yaml_format=False,
        )
    except SystemExit as e:
        exit_code = e.code if isinstance(e.code, int) else 0 if e.code is None else 1
        if exit_code != 0:
            raise
    except ValueError as e:
        raise typer.BadParameter(str(e)) from e

    separator_path = Path(".ai") / "agents" / job_name / "separator.txt"
    separator_path.parent.mkdir(parents=True, exist_ok=True)
    separator_path.write_text(normalized_separator, encoding="utf-8")
