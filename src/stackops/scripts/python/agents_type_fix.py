from typing import Annotated, Literal, cast
from contextlib import redirect_stdout
from dataclasses import replace
import json
from pathlib import Path
import sys

import typer

from stackops.utils.default_agent import DEFAULT_AGENT_HELP
from stackops.utils.schemas.fire_agents.fire_agents_types import AGENTS
from stackops.scripts.python.helpers.helpers_agents.agents_impl import AgentsDirectoryConflict
from stackops.scripts.python.ai.scripts.models_core import REPORTS_DIR
from stackops.scripts.python.helpers.helpers_agents.type_check_context import read_type_check_report


PROMPT = """please fix those, but don't be so pedantic because the linter and type checker are not perfect and occasionally give false positives
in which case it is okay to ignore them and leave code as is, if you felt like that.
Use only the diagnostics in your JSON batch. Each diagnosticValue is the tool's original diagnostic;
diagnosticNumber refers to its position in the original report.
"""


def launch_type_fix(
    ctx: typer.Context,
    agent: Annotated[AGENTS | None, typer.Option("--agent", "-a", help=f"Agent type. {DEFAULT_AGENT_HELP}")] = None,
    agent_load: Annotated[int, typer.Option("--agent-load", "-l", min=1, help="Number of diagnostics per prompt.")] = 10,
    which_checker: Annotated[
        Literal["mypy", "ruff", "pylint", "pyright", "ty", "pyrefly"],
        typer.Option("--which-checker", "--which", "-w", help="Which issues_<checker>.json file under ./.ai/linters to process."),
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

    issues_path: Path = REPORTS_DIR / f"""issues_{which_checker}.json"""
    try:
        report = read_type_check_report(cast(object, json.loads(issues_path.read_text(encoding="utf-8"))))
        if report["tool"] != which_checker:
            raise ValueError(f"""Expected {which_checker} diagnostics, found {report['tool']} in {issues_path}""")
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error
    if not report["diagnostics"]:
        if json_output:
            from stackops.scripts.python.helpers.helpers_agents.agents_json import emit_agent_json

            emit_agent_json({"tool": which_checker, "agent_count": 0, "launched": False})
        else:
            typer.echo(f"""No diagnostics reported by {which_checker}; no agents created.""")
        return
    with redirect_stdout(sys.stderr if json_output else sys.stdout):
        result = agents_create_command(
            agent=agent,
            context_path=str(issues_path),
            agent_load=agent_load,
            prompt=PROMPT,
            job_name=f"""fix_{which_checker}_issues""",
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
