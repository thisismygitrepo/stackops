from pathlib import Path
from typing import Annotated

import typer

from stackops.scripts.python.helpers.helpers_agents.agents_iter_constants import (
    CLOSE_LOOP_INTERVAL_SECONDS,
    DEFAULT_RETAIN_PREVIOUS_ITERATIONS,
    DEFAULT_TRACK_MAX_ITERATIONS,
    TRACK_INTERVAL_SECONDS,
)


def close(
    space_name: Annotated[
        str | None,
        typer.Argument(help="Herdr iter workspace label or stable ID to close. Use --all for every iter workspace."),
    ] = None,
    continuous: Annotated[bool, typer.Option("--loop", "-l", help="Repeat close passes until interrupted.")] = False,
    all_workspaces: Annotated[
        bool,
        typer.Option("--all", "-a", help="Close old idle tabs in all iter workspaces."),
    ] = False,
    retain_previous: Annotated[
        int,
        typer.Option(
            "--retain-previous",
            "-k",
            min=0,
            help="Retain the latest iteration plus this many previous iterations.",
        ),
    ] = DEFAULT_RETAIN_PREVIOUS_ITERATIONS,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show the close plan without closing tabs.")] = False,
    interval_seconds: Annotated[
        int,
        typer.Option("--interval", "-i", min=1, help="Seconds between close passes when --loop is used."),
    ] = CLOSE_LOOP_INTERVAL_SECONDS,
) -> None:
    """Safely close old idle iteration tabs after revalidating their live state."""
    try:
        from stackops.scripts.python.helpers.helpers_agents.agents_iter_rich_output import show_close_iter_workspaces_loop

        show_close_iter_workspaces_loop(
            workspace_name=space_name,
            all_workspaces=all_workspaces,
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


def clean(
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show stale iteration records without removing them.")] = False,
) -> None:
    """Remove stale iteration records while preserving live and unrelated AgentOps records."""
    try:
        from stackops.scripts.python.helpers.helpers_agents.agents_iter_rich_output import show_clean_agentops_cache

        show_clean_agentops_cache(cwd=Path.cwd(), dry_run=dry_run)
    except RuntimeError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error


def track(
    space_name: Annotated[str, typer.Argument(help="Herdr iter workspace label or stable ID to track.")],
    max_iterations: Annotated[int, typer.Argument(help="Maximum allowed iteration number before the workspace is closed.")] = DEFAULT_TRACK_MAX_ITERATIONS,
    interval_seconds: Annotated[
        int,
        typer.Option("--interval", "-i", min=1, help="Seconds to sleep between iteration-budget checks."),
    ] = TRACK_INTERVAL_SECONDS,
    retain_previous: Annotated[
        int,
        typer.Option(
            "--retain-previous",
            "-k",
            min=0,
            help="Retain the latest iteration plus this many previous iterations.",
        ),
    ] = DEFAULT_RETAIN_PREVIOUS_ITERATIONS,
) -> None:
    """Track an iter Herdr workspace status, close old iteration tabs, and close after budget."""
    try:
        from stackops.scripts.python.helpers.helpers_agents.agents_iter_rich_output import show_track_iter_workspace_loop

        show_track_iter_workspace_loop(
            workspace_name=space_name,
            max_iterations=max_iterations,
            interval_seconds=interval_seconds,
            retain_previous=retain_previous,
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except RuntimeError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error


def status(
    retain_previous: Annotated[
        int,
        typer.Option(
            "--retain-previous",
            "-k",
            min=0,
            help="Evaluate closable tabs while retaining this many previous iterations.",
        ),
    ] = DEFAULT_RETAIN_PREVIOUS_ITERATIONS,
) -> None:
    """Show each iter loop's latest iteration agent and live Herdr status."""
    try:
        from stackops.scripts.python.helpers.helpers_agents.agents_iter_rich_output import show_iter_status

        show_iter_status(retain_previous=retain_previous)
    except RuntimeError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error


def get_app() -> typer.Typer:
    iter_app = typer.Typer(help="🔁 <I> Iter workflow maintenance commands", no_args_is_help=True, add_help_option=True, add_completion=False)
    iter_app.command(name="clean", no_args_is_help=False, short_help="<c> Remove stale iter records under .ai")(clean)
    iter_app.command(name="c", no_args_is_help=False, hidden=True)(clean)
    iter_app.command(name="close", no_args_is_help=False, short_help="<x> Revalidate and close old idle iter tabs")(close)
    iter_app.command(name="x", no_args_is_help=False, hidden=True)(close)
    iter_app.command(name="track", no_args_is_help=False, short_help="<t> Track, prune old tabs, and enforce budget")(track)
    iter_app.command(name="t", no_args_is_help=False, hidden=True)(track)
    iter_app.command(name="status", no_args_is_help=False, short_help="<s> Show live iter state and safe close counts")(status)
    iter_app.command(name="s", no_args_is_help=False, hidden=True)(status)
    return iter_app
