from typing import Annotated, Literal, TypeAlias

import typer

from machineconfig.scripts.python.agents_parallel_commands import agents_create as agents_create_command
from machineconfig.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AGENTS
from machineconfig.scripts.python.terminal import run as terminal_run_command


CheckerName: TypeAlias = Literal["mypy", "ruff", "pylint", "pyright", "ty", "pyrefly"]
DIAGNOSTIC_SEPARATOR = "### Diagnostic"
PROMPT = "please fix those, but don't be so pedantic because the linter and type checker are not perfect and occasionally give false positives"


def _get_issues_path(*, checker_name: CheckerName) -> str:
    return f"./.ai/linters/issues_{checker_name}.md"


def _get_job_name(*, checker_name: CheckerName) -> str:
    return f"fix_{checker_name}_issues"


def _get_layout_path(*, checker_name: CheckerName) -> str:
    return f"./.ai/agents/{_get_job_name(checker_name=checker_name)}/layout.json"


def launch_type_fix(
    ctx: typer.Context,
    agent: Annotated[AGENTS, typer.Option("--agent", "-a", help="Agent type.")] = "codex",
    agent_load: Annotated[int, typer.Option("--agent-load", "-l", help="Number of diagnostics per prompt.")] = 10,
    which_checker: Annotated[
        CheckerName,
        typer.Option("--which-checker", "--which", "-w", help="Which issues_<checker>.md file under ./.ai/linters to process."),
    ] = "mypy",
    max_tabs: Annotated[
        int,
        typer.Option("--max-agents", "-m", help="Maximum agents allowed in the generated layout."),
    ] = 50,
) -> None:
    job_name = _get_job_name(checker_name=which_checker)
    agents_create_command(
        agent=agent,
        context_path=_get_issues_path(checker_name=which_checker),
        separator=DIAGNOSTIC_SEPARATOR,
        agent_load=agent_load,
        prompt=PROMPT,
        job_name=job_name,
    )
    proceed = typer.confirm(f"Agents layout for fixing {which_checker} issues created. Do you want to run it now?", default=True)
    if not proceed:
        typer.echo("Agents not luanched.")
        return
    terminal_run_command(
        ctx=ctx,
        layouts_file=_get_layout_path(checker_name=which_checker),
        max_tabs=max_tabs,
        on_conflict="restart",
    )


def get_app() -> typer.Typer:
    cli_app = typer.Typer(
        help="🛠 <f> Create and run the type-fix workflow from ./.ai/linters issues files.",
        no_args_is_help=True,
        add_help_option=True,
        add_completion=False,
    )
    cli_app.callback(invoke_without_command=True)(launch_type_fix)
    return cli_app