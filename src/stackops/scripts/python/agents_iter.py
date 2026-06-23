from typing import Annotated

import typer


def clean(continuous: Annotated[bool, typer.Option("--loop", "-l", help="Repeat cleanup every 5 minutes.")] = False) -> None:
    """Close old Herdr tabs in iter workspaces, keeping the last 3 tabs per workspace."""
    try:
        from stackops.scripts.python.helpers.helpers_agents.agents_iter_impl import clean_iter_workspaces_loop

        clean_iter_workspaces_loop(continuous=continuous, report=typer.echo)
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
    iter_app = typer.Typer(help="🔁 <c> Iter workflow maintenance commands", no_args_is_help=True, add_help_option=True, add_completion=False)
    iter_app.command(name="clean", no_args_is_help=False, short_help="<c> Clean old Herdr tabs from iter workspaces")(clean)
    iter_app.command(name="c", no_args_is_help=False, hidden=True)(clean)
    iter_app.command(name="status", no_args_is_help=False, short_help="<s> Show iter workspace status")(status)
    iter_app.command(name="s", no_args_is_help=False, hidden=True)(status)
    return iter_app
