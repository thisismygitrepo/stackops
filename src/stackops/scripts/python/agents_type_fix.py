from typing import Annotated, Literal, TypeAlias
from contextlib import redirect_stdout
from dataclasses import replace
import sys

import typer

from stackops.utils.default_agent import DEFAULT_AGENT_HELP
from stackops.utils.schemas.fire_agents.fire_agents_types import AGENTS
from stackops.scripts.python.helpers.helpers_agents.agents_impl import AgentsDirectoryConflict


CheckerName: TypeAlias = Literal["mypy", "ruff", "pylint", "pyright", "ty", "pyrefly"]
DIAGNOSTIC_SEPARATOR = "### Diagnostic"
PROMPT = """please fix those, but don't be so pedantic because the linter and type checker are not perfect and occasionally give false positives
in which case it is okay to ignore them and leave code as is, if you felt like that.
"""


def _get_issues_path(*, checker_name: CheckerName) -> str:
    return f"./.ai/linters/issues_{checker_name}.md"


def _get_job_name(*, checker_name: CheckerName) -> str:
    return f"fix_{checker_name}_issues"


def _get_layout_path(*, checker_name: CheckerName) -> str:
    return f"./.ai/agents/{_get_job_name(checker_name=checker_name)}/layout.yaml"


def launch_type_fix(
    ctx: typer.Context,
    agent: Annotated[AGENTS | None, typer.Option("--agent", "-a", help=f"Agent type. {DEFAULT_AGENT_HELP}")] = None,
    agent_load: Annotated[int, typer.Option("--agent-load", "-l", help="Number of diagnostics per prompt.")] = 10,
    which_checker: Annotated[
        CheckerName,
        typer.Option("--which-checker", "--which", "-w", help="Which issues_<checker>.md file under ./.ai/linters to process."),
    ] = "mypy",
    max_tabs: Annotated[
        int,
        typer.Option("--max-agents", "-m", help="Maximum agents allowed in the generated layout."),
    ] = 50,
    run: Annotated[bool, typer.Option("--run", "-R", help="Launch the generated agents; by default only prepare their artifacts.")] = False,
    on_directory_conflict: Annotated[AgentsDirectoryConflict, typer.Option("--on-directory-conflict", "-D", help="Existing agents directory: error, new-directory, or replace-owned.")] = "error",
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Print generated artifact paths and launch state as JSON.")] = False,
) -> None:
    from stackops.scripts.python.agents_parallel_commands import agents_create as agents_create_command

    job_name = _get_job_name(checker_name=which_checker)
    with redirect_stdout(sys.stderr if json_output else sys.stdout):
        result = agents_create_command(
            agent=agent,
            context_path=_get_issues_path(checker_name=which_checker),
            separator=DIAGNOSTIC_SEPARATOR,
            agent_load=agent_load,
            prompt=PROMPT,
            job_name=job_name,
            on_directory_conflict=on_directory_conflict,
            run=False,
        )
        if result is None:
            raise RuntimeError("Type-fix generation did not return artifact paths")
        if run:
            from stackops.scripts.python.terminal import run as terminal_run_command

            terminal_run_command(ctx=ctx, layouts_file=str(result.layout_path), max_tabs=max_tabs, on_conflict="restart", attach=False)
    if json_output:
        from stackops.scripts.python.helpers.helpers_agents.agents_json import emit_agent_json

        emit_agent_json(replace(result, launched=run))


def get_app() -> typer.Typer:
    cli_app = typer.Typer(
        help="🔧 <f> Create and run the type-fix workflow from ./.ai/linters issues files.",
        no_args_is_help=True,
        add_help_option=True,
        add_completion=False,
        context_settings={"help_option_names": ["-h", "--help"]},
    )
    cli_app.callback(invoke_without_command=True)(launch_type_fix)
    return cli_app
