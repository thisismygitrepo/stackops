from pathlib import Path
from typing import Annotated

import typer

from stackops.scripts.python.helpers.helpers_agents.agents_iter_constants import DEFAULT_TRACK_MAX_ITERATIONS, TRACK_INTERVAL_SECONDS


def close(
    space_name: Annotated[
        str | None,
        typer.Argument(help="Exact Herdr iter workspace label to close. Use --all to close every iter workspace."),
    ] = None,
    continuous: Annotated[bool, typer.Option("--loop", "-l", help="Repeat close pass every 5 minutes.")] = False,
    all_workspaces: Annotated[
        bool,
        typer.Option("--all", "-a", help="Close old idle tabs in all iter workspaces."),
    ] = False,
) -> None:
    """Close old idle Herdr tabs in one iter workspace, or all iter workspaces with --all."""
    try:
        from stackops.scripts.python.helpers.helpers_agents.agents_iter_impl import close_iter_workspaces_loop

        close_iter_workspaces_loop(
            workspace_name=space_name,
            all_workspaces=all_workspaces,
            continuous=continuous,
            report=typer.echo,
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except RuntimeError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error


def clean() -> None:
    """Clean workflow cache records under .ai."""
    try:
        from stackops.scripts.python.helpers.helpers_agents.agents_workflow_cache import clean_workflow_cache

        clean_workflow_cache(cwd=Path.cwd(), report=typer.echo)
    except RuntimeError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error


def track(
    space_name: Annotated[str, typer.Argument(help="Exact Herdr iter workspace label to track.")],
    max_iterations: Annotated[int, typer.Argument(help="Maximum allowed iteration number before the workspace is closed.")] = DEFAULT_TRACK_MAX_ITERATIONS,
    interval_seconds: Annotated[
        int,
        typer.Option("--interval", "-i", min=1, help="Seconds to sleep between iteration-budget checks."),
    ] = TRACK_INTERVAL_SECONDS,
) -> None:
    """Track an iter Herdr workspace and close it after it exceeds the iteration budget."""
    try:
        from stackops.scripts.python.helpers.helpers_agents.agents_iter_impl import track_iter_workspace_loop

        track_iter_workspace_loop(
            workspace_name=space_name,
            max_iterations=max_iterations,
            interval_seconds=interval_seconds,
            report=typer.echo,
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except RuntimeError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error


def status() -> None:
    """Show each iter loop's latest iteration agent and live Herdr status."""
    try:
        from stackops.scripts.python.helpers.helpers_agents.agents_iter_impl import show_iter_status

        show_iter_status()
    except RuntimeError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error


def get_app() -> typer.Typer:
    iter_app = typer.Typer(help="🔁 <I> Iter workflow maintenance commands", no_args_is_help=True, add_help_option=True, add_completion=False)
    iter_app.command(name="clean", no_args_is_help=False, short_help="<c> Clean workflow cache under .ai")(clean)
    iter_app.command(name="c", no_args_is_help=False, hidden=True)(clean)
    iter_app.command(name="close", no_args_is_help=False, short_help="<x> Close old idle Herdr tabs from iter workspaces")(close)
    iter_app.command(name="x", no_args_is_help=False, hidden=True)(close)
    iter_app.command(name="track", no_args_is_help=False, short_help="<t> Track and close an iter workspace after its budget")(track)
    iter_app.command(name="t", no_args_is_help=False, hidden=True)(track)
    iter_app.command(name="status", no_args_is_help=False, short_help="<s> Show iter workspace status")(status)
    iter_app.command(name="s", no_args_is_help=False, hidden=True)(status)
    return iter_app
