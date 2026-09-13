from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast, get_args

import click
import typer

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_models import CleanupPlan, CleanupScope
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.command import resolve_resource_focuses
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorResourceFocus
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.registry import DOCTOR_AGENT_ALIASES, DOCTOR_DEFINITION_BY_AGENT


@dataclass(frozen=True)
class CleanupSelection:
    agent: str
    directory: str
    scope: CleanupScope
    resource: str
    match: str | None


def prompt_cleanup_selection(*, selection: CleanupSelection) -> CleanupSelection:
    typer.echo("Step 1/4: Choose what to inspect and reset.")
    agent: str = typer.prompt(
        "Agent", default=selection.agent,
        type=click.Choice(("all", *DOCTOR_DEFINITION_BY_AGENT, *DOCTOR_AGENT_ALIASES), case_sensitive=False),
    )
    directory: str = typer.prompt(
        "Project directory", default=selection.directory,
        type=click.Path(exists=True, file_okay=False),
    )
    typer.echo("Scope: local = project configuration; global = user configuration; all = both plus managed resources.")
    scope = cast(CleanupScope, typer.prompt(
        "Scope", default=selection.scope, type=click.Choice(get_args(CleanupScope), case_sensitive=False),
    ))
    typer.echo(f"""Resources (comma-separated): {', '.join(get_args(DoctorResourceFocus))}.""")
    typer.echo("Choosing all includes resetting whole configuration files and plugin installation directories.")
    while True:
        resource: str = typer.prompt("Resources", default=selection.resource)
        try:
            resolve_resource_focuses(requested_resources=resource)
            break
        except ValueError as error:
            typer.echo(f"""Invalid selection: {error}""", err=True)
    match: str | None = None
    if typer.confirm("Filter by name, command, or source path?", default=selection.match is not None):
        while True:
            match = cast(str, typer.prompt("Match", default=selection.match))
            if match.strip():
                break
            typer.echo("Enter a nonempty name, command, or source path.", err=True)
    return CleanupSelection(agent=agent, directory=directory, scope=scope, resource=resource, match=match)


def choose_cleanup_action(*, plan: CleanupPlan, backup_root: Path) -> Literal["apply", "revise", "exit"]:
    if plan.blockers:
        typer.echo("Status: blocked. Revise the selection or resolve the errors shown above before resetting.")
    elif not plan.changes:
        typer.echo("Status: nothing to reset for this selection.")
    else:
        typer.echo(f"""Status: ready to reset {len(plan.changes)} path(s). Originals will be saved under {backup_root}.""")
    choices = ("revise", "exit") if plan.blockers or not plan.changes else ("apply", "revise", "exit")
    action = cast(Literal["apply", "revise", "exit"], typer.prompt(
        "Next action", type=click.Choice(choices, case_sensitive=False), default="exit",
    ))
    if action == "apply" and not typer.confirm("Apply the displayed reset and preserve backups?", default=False):
        typer.echo("Reset cancelled. No files changed.")
        return "exit"
    return action
