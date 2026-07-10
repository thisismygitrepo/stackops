from pathlib import Path
from typing import Annotated

import typer

from stackops.scripts.python.helpers.helpers_agents.agents_iter_constants import (
    CLOSE_LOOP_INTERVAL_SECONDS,
    DEFAULT_RETAIN_PREVIOUS_ITERATIONS,
    HERDR_VERSION,
)


def close(
    workspace_id: Annotated[str, typer.Argument(help="Stable Herdr iter workspace ID to prune.")],
    continuous: Annotated[bool, typer.Option("--loop", "-l", help="Repeat close passes until interrupted.")] = False,
    retain_previous: Annotated[
        int, typer.Option("--retain-previous", "-k", min=0, help="Retain the latest iteration plus this many previous iterations.")
    ] = DEFAULT_RETAIN_PREVIOUS_ITERATIONS,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show the close plan without closing tabs.")] = False,
    interval_seconds: Annotated[
        int, typer.Option("--interval", "-i", min=1, help="Seconds between close passes when --loop is used.")
    ] = CLOSE_LOOP_INTERVAL_SECONDS,
) -> None:
    """Close handed-off iteration tabs after exact receipt and live-state validation."""
    try:
        from stackops.scripts.python.helpers.helpers_agents.agents_iter_rich_output import show_close_iter_workspace_loop

        show_close_iter_workspace_loop(
            cwd=Path.cwd(),
            workspace_id=workspace_id,
            continuous=continuous,
            retain_previous=retain_previous,
            dry_run=dry_run,
            interval_seconds=interval_seconds,
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except RuntimeError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error


def clean(dry_run: Annotated[bool, typer.Option("--dry-run", help="Show stale iteration records without removing them.")] = False) -> None:
    """Remove stale iteration records while preserving live and unrelated AgentOps records."""
    try:
        from stackops.scripts.python.helpers.helpers_agents.agents_iter_rich_output import show_clean_agentops_cache

        show_clean_agentops_cache(cwd=Path.cwd(), dry_run=dry_run)
    except RuntimeError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error


def status(
    retain_previous: Annotated[
        int, typer.Option("--retain-previous", "-k", min=0, help="Evaluate closable tabs while retaining this many previous iterations.")
    ] = DEFAULT_RETAIN_PREVIOUS_ITERATIONS,
) -> None:
    """Show each iter loop's latest iteration agent and live Herdr status."""
    try:
        from stackops.scripts.python.helpers.helpers_agents.agents_iter_rich_output import show_iter_status

        show_iter_status(cwd=Path.cwd(), retain_previous=retain_previous)
    except RuntimeError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error


def get_app() -> typer.Typer:
    iter_app = typer.Typer(
        help=f"🔁 <I> Iter maintenance for Herdr {HERDR_VERSION}", no_args_is_help=True, add_help_option=True, add_completion=False
    )
    iter_app.command(name="clean", no_args_is_help=False, short_help="<c> Remove stale iter records under .ai")(clean)
    iter_app.command(name="c", no_args_is_help=False, hidden=True)(clean)
    iter_app.command(name="close", no_args_is_help=False, short_help="<x> Close verified handed-off iter tabs")(close)
    iter_app.command(name="x", no_args_is_help=False, hidden=True)(close)
    iter_app.command(name="status", no_args_is_help=False, short_help="<s> Show live state and verified close counts")(status)
    iter_app.command(name="s", no_args_is_help=False, hidden=True)(status)
    return iter_app
