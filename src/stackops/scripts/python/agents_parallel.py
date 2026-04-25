"""Parallel agent workflow commands."""

from typing import get_args

import typer

from stackops.scripts.python.agents_parallel_commands import agents_create, collect, create_context, make_agents_command_template
from stackops.scripts.python.agents_parallel_run_command import run_parallel
from stackops.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AGENTS, PROVIDER


def get_app() -> typer.Typer:
    parallel_app = typer.Typer(
        help="🧵 <p> Parallel agent workflow commands",
        no_args_is_help=True,
        add_help_option=True,
        add_completion=False,
    )
    sep = "\n"
    agents_full_help = f"""
<c> Create agents layout file, ready to run.
{sep}
PROVIDER options: {", ".join(get_args(PROVIDER))}
{sep}
AGENT options: {", ".join(get_args(AGENTS))}
"""
    agents_create.__doc__ = agents_full_help
    parallel_app.command(
        "create",
        no_args_is_help=True,
        help=agents_create.__doc__,
        short_help="<c> Create agents layout file, ready to run.",
    )(agents_create)
    parallel_app.command("c", no_args_is_help=True, help=agents_create.__doc__, hidden=True)(agents_create)
    parallel_app.command(
        name="create-context",
        no_args_is_help=True,
        short_help="<x> Run prompt and ask agent to persist context",
    )(create_context)
    parallel_app.command(name="x", no_args_is_help=True, hidden=True)(create_context)
    parallel_app.command(
        name="run-parallel",
        no_args_is_help=False,
        short_help="<r> Run named parallel workflow from YAML",
    )(run_parallel)
    parallel_app.command(name="r", no_args_is_help=False, hidden=True)(run_parallel)
    parallel_app.command(
        "collect",
        no_args_is_help=True,
        help=collect.__doc__,
        short_help="<T> Collect all agent materials into a single file.",
    )(collect)
    parallel_app.command("T", no_args_is_help=True, help=collect.__doc__, hidden=True)(collect)
    parallel_app.command(
        "make-template",
        no_args_is_help=False,
        help=make_agents_command_template.__doc__,
        short_help="<p> Create a template for fire agents",
    )(make_agents_command_template)
    parallel_app.command("p", no_args_is_help=False, help=make_agents_command_template.__doc__, hidden=True)(make_agents_command_template)
    return parallel_app
