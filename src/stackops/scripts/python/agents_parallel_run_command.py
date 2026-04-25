"""Run-parallel command wrapper."""

from typing import Annotated, get_args

import typer

from stackops.scripts.python.helpers.helpers_agents.agents_parallel_run_config import PARALLEL_RUNS_WHERE, ParallelCreateValues
from stackops.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AGENTS, HOST, PROVIDER
from stackops.scripts.python.helpers.helpers_agents.reasoning_capabilities import ReasoningEffort


def run_parallel(
    config_name: Annotated[str | None, typer.Argument(help="Parallel YAML run name. Supports dot paths, e.g. docs.update.")] = None,
    parallel_yaml_path: Annotated[
        str | None,
        typer.Option(
            ...,
            "--parallel-yaml-path",
            "-y",
            help="YAML file containing named parallel runs. Auto-created with a template if missing.",
        ),
    ] = None,
    where: Annotated[
        PARALLEL_RUNS_WHERE,
        typer.Option(..., "--where", "-w", help="Where to look for parallel YAML files when --parallel-yaml-path is not provided."),
    ] = "all",
    show_parallel_yaml_format: Annotated[
        bool,
        typer.Option(..., "--show-format", "-Y", help="Show parallel YAML format guidance and resolved file paths."),
    ] = False,
    edit: Annotated[
        bool,
        typer.Option(..., "--edit", "-e", help="Open parallel YAML in an editor (hx preferred, nano fallback)."),
    ] = False,
    agent: Annotated[AGENTS | None, typer.Option(..., "--agent", "-a", help="Override agent type.")] = None,
    model: Annotated[str | None, typer.Option(..., "--model", "-m", help="Override model.")] = None,
    reasoning_effort: Annotated[
        ReasoningEffort | None,
        typer.Option(..., "--reasoning-effort", "-r", help="Override reasoning effort for codex and pi agents."),
    ] = None,
    provider: Annotated[PROVIDER | None, typer.Option(..., "--provider", "-v", help="Override provider.")] = None,
    host: Annotated[HOST | None, typer.Option(..., "--host", "-h", help=f"Override machine. One of {', '.join(get_args(HOST))}")] = None,
    context: Annotated[
        str | None, typer.Option(..., "--context", "-c", help="Override context as a direct string. Mutually exclusive with --context-path.")
    ] = None,
    context_path: Annotated[str | None, typer.Option(..., "--context-path", "-C", help="Override context file/folder path.")] = None,
    separator: Annotated[
        str | None, typer.Option(..., "--separator", "-s", help="Override separator for context. Supports escaped values like '\\n'.")
    ] = None,
    agent_load: Annotated[int | None, typer.Option(..., "--agent-load", "-l", help="Override number of tasks per prompt.")] = None,
    prompt: Annotated[str | None, typer.Option(..., "--prompt", "-p", help="Override prompt prefix as string.")] = None,
    prompt_path: Annotated[str | None, typer.Option(..., "--prompt-path", "-P", help="Override prompt file path.")] = None,
    prompt_name: Annotated[str | None, typer.Option(..., "--prompt-name", "-N", help="Override prompt entry name from prompts YAML.")] = None,
    job_name: Annotated[
        str | None,
        typer.Option(..., "--job-name", "-n", help="Override job label. Also used as generated layout name and default output directory."),
    ] = None,
    join_prompt_and_context: Annotated[
        bool | None,
        typer.Option(
            ...,
            "--joined-prompt-context/--no-joined-prompt-context",
            "-j/-J",
            help="Override whether to join prompt file to the context.",
        ),
    ] = None,
    output_path: Annotated[str | None, typer.Option(..., "--output-path", "-o", help="Override layout.json output path.")] = None,
    agents_dir: Annotated[str | None, typer.Option(..., "--agents-dir", "-d", help="Override exact directory to store agent files in.")] = None,
    interactive: Annotated[
        bool | None,
        typer.Option(..., "--interactive/--no-interactive", "-i/-I", help="Override whether to run create in interactive mode."),
    ] = None,
) -> None:
    """Run a named parallel agent workflow from YAML, with create-option overrides."""
    from stackops.scripts.python.helpers.helpers_agents.agents_parallel_run_impl import run_parallel_from_yaml

    try:
        run_parallel_from_yaml(
            config_name=config_name,
            parallel_yaml_path=parallel_yaml_path,
            where=where,
            overrides=ParallelCreateValues(
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
            ),
            edit=edit,
            show_parallel_yaml_format=show_parallel_yaml_format,
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except RuntimeError as error:
        typer.echo(str(error))
        raise typer.Exit(1) from error
