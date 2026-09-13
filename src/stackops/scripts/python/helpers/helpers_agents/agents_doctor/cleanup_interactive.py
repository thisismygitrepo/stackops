from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast, get_args

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


def _prompt_choice(*, label: str, choices: tuple[str, ...], default: str) -> str:
    def validate_choice(value: str) -> str:
        normalized = value.casefold()
        if normalized not in choices:
            raise typer.BadParameter(f"""Choose one of: {', '.join(choices)}.""")
        return normalized

    return cast(str, typer.prompt(
        f"""{label} ({', '.join(choices)})""", default=default, value_proc=validate_choice,
    ))


def _validate_directory(value: str) -> str:
    if not Path(value).is_dir():
        raise typer.BadParameter(f"""Directory '{value}' does not exist or is not a directory.""")
    return value


def prompt_cleanup_selection(*, selection: CleanupSelection) -> CleanupSelection:
    typer.echo("Step 1/4: Choose what to inspect and reset.")
    agent = _prompt_choice(
        label="Agent", default=selection.agent,
        choices=("all", *DOCTOR_DEFINITION_BY_AGENT, *DOCTOR_AGENT_ALIASES),
    )
    directory: str = typer.prompt(
        "Project directory", default=selection.directory,
        value_proc=_validate_directory,
    )
    typer.echo("Scope: local = project configuration; global = user configuration; all = both plus managed resources.")
    scope = cast(CleanupScope, _prompt_choice(
        label="Scope", default=selection.scope, choices=get_args(CleanupScope),
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
    action = cast(Literal["apply", "revise", "exit"], _prompt_choice(
        label="Next action", choices=choices, default="exit",
    ))
    if action == "apply" and not typer.confirm("Apply the displayed reset and preserve backups?", default=False):
        typer.echo("Reset cancelled. No files changed.")
        return "exit"
    return action
