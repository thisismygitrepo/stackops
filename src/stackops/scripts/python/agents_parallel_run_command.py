"""Named parallel workflow command."""

from typing import Annotated, Literal, TypeAlias, get_args

import typer

from stackops.scripts.python.helpers.helpers_agents.agents_parallel_backend import (
    AgentParallelBackendOption,
)
from stackops.utils.schemas.fire_agents.fire_agents_types import AGENTS, HOST, PROVIDER, ReasoningEffort

_PARALLEL_RUNS_SOURCE = Literal["all", "a", "workspace", "w", "user", "u", "library", "l"]
_BooleanOverride: TypeAlias = Literal["true", "false"]


def run_parallel(
    run_name: Annotated[str | None, typer.Argument(help="Parallel YAML run name. Use a flat top-level key, e.g. docs_update.")] = None,
    custom_path: Annotated[
        str | None, typer.Option(..., "--custom-path", "-y", help="Custom YAML file containing named parallel runs. Use --edit or --add-entry to create a missing file.")
    ] = None,
    source: Annotated[
        _PARALLEL_RUNS_SOURCE,
        typer.Option(..., "--source", "-S", help="Source to look for parallel YAML files when --custom-path is not provided."),
    ] = "all",
    show_parallel_yaml_format: Annotated[
        bool, typer.Option(..., "--show-format", "-Y", help="Show parallel YAML format guidance and resolved file paths.")
    ] = False,
    edit: Annotated[
        bool,
        typer.Option(
            ..., "--edit", "-e",
            help="Edit parallel YAML (hx preferred, nano fallback). Choose one source interactively unless --source or --custom-path specifies it.",
        ),
    ] = False,
    add_entry: Annotated[
        bool,
        typer.Option(
            ...,
            "--add-entry",
            "-A",
            help="Append one default template entry to workspace parallel YAML. Use --source or --custom-path to choose the target, or --edit to choose and open it. If RUN_NAME is provided, use it as the new entry name.",
        ),
    ] = False,
    agent: Annotated[AGENTS | None, typer.Option(..., "--agent", "-a", help="Override agent type.")] = None,
    model: Annotated[str | None, typer.Option(..., "--model", "-m", help="Override model.")] = None,
    reasoning_effort: Annotated[
        ReasoningEffort | None,
        typer.Option(..., "--reasoning", "-r", help="Override reasoning effort for codex, copilot, cortex, and pi agents. Unsupported agents ignore it."),
    ] = None,
    provider: Annotated[PROVIDER | None, typer.Option(..., "--provider", "-v", help="Override provider.")] = None,
    host: Annotated[HOST | None, typer.Option(..., "--host", "-H", help=f"Override machine. One of {', '.join(get_args(HOST))}")] = None,
    backend: Annotated[
        AgentParallelBackendOption | None,
        typer.Option(..., "--backend", "-b", help="Override backend used when --run launches the generated layout."),
    ] = None,
    context: Annotated[
        str | None, typer.Option(..., "--context", "-c", help="Override context as a direct string. Mutually exclusive with --context-path.")
    ] = None,
    context_path: Annotated[str | None, typer.Option(..., "--context-path", "-C", help="Override context file/folder path.")] = None,
    separator: Annotated[
        str | None, typer.Option(..., "--separator", "-s", help="Override separator for context. Supports escaped values like '\\n'.")
    ] = None,
    agent_load: Annotated[int | None, typer.Option(..., "--agent-load", "-l", help="Override number of tasks per prompt.")] = None,
    stagger_max: Annotated[
        float | None,
        typer.Option(..., "--stagger-max", "-g", min=0.0, help="Override maximum startup stagger delay, in seconds. Use 0 to disable staggering."),
    ] = None,
    prompt: Annotated[str | None, typer.Option(..., "--prompt", "-p", help="Override prompt prefix as string.")] = None,
    prompt_path: Annotated[str | None, typer.Option(..., "--prompt-path", "-P", help="Override prompt file path.")] = None,
    prompt_name: Annotated[str | None, typer.Option(..., "--prompt-name", "-N", help="Override prompt entry name from prompts YAML.")] = None,
    job_name: Annotated[
        str | None, typer.Option(..., "--job-name", "-n", help="Override job label. Also used as generated layout name and default output directory.")
    ] = None,
    join_prompt_and_context: Annotated[
        _BooleanOverride | None,
        typer.Option("--join-prompt-context", "-j", help="Override whether the prompt file is joined to the context: true or false. Omit to use YAML."),
    ] = None,
    run: Annotated[
        _BooleanOverride | None,
        typer.Option("--run", "-R", help="Override whether the layout launches immediately: true or false. Omit to use YAML; launches when YAML omits run."),
    ] = None,
    output_path: Annotated[str | None, typer.Option(..., "--output", "-o", help="Override layout.yaml output path.")] = None,
    agents_dir: Annotated[str | None, typer.Option(..., "--agents-dir", "-d", help="Override exact directory to store agent files in.")] = None,
    interactive: Annotated[
        _BooleanOverride | None, typer.Option("--interactive", "-i", help="Override whether create runs interactively: true or false. Omit to use YAML.")
    ] = None,
) -> None:
    """Run a named parallel agent workflow from YAML, with create-option overrides."""
    from stackops.scripts.python.helpers.helpers_agents.agents_parallel_backend import resolve_agent_parallel_backend
    from stackops.scripts.python.helpers.helpers_agents.agents_parallel_run_config import ParallelCreateValues
    from stackops.scripts.python.helpers.helpers_agents.agents_parallel_run_impl import run_parallel_from_yaml

    try:
        run_parallel_from_yaml(
            config_name=run_name,
            parallel_yaml_path=custom_path,
            source=source,
            overrides=ParallelCreateValues(
                agent=agent,
                model=model,
                reasoning_effort=reasoning_effort,
                provider=provider,
                host=host,
                backend=None if backend is None else resolve_agent_parallel_backend(backend),
                context=context,
                context_path=context_path,
                separator=separator,
                agent_load=agent_load,
                stagger_max=stagger_max,
                prompt=prompt,
                prompt_path=prompt_path,
                prompt_name=prompt_name,
                job_name=job_name,
                join_prompt_and_context=None if join_prompt_and_context is None else join_prompt_and_context == "true",
                run=None if run is None else run == "true",
                output_path=output_path,
                agents_dir=agents_dir,
                interactive=None if interactive is None else interactive == "true",
            ),
            edit=edit,
            add_entry=add_entry,
            show_parallel_yaml_format=show_parallel_yaml_format,
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except RuntimeError as error:
        typer.echo(str(error))
        raise typer.Exit(1) from error
