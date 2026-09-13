from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast, get_args

import typer
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

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


def prompt_cleanup_selection(*, console: Console, selection: CleanupSelection) -> CleanupSelection:
    console.print(Rule("Step 1/4 · Choose reset targets", style="cyan"))
    agent = _prompt_choice(
        label="Agent", default=selection.agent,
        choices=("all", *DOCTOR_DEFINITION_BY_AGENT, *DOCTOR_AGENT_ALIASES),
    )
    directory: str = typer.prompt(
        "Project directory", default=selection.directory,
        value_proc=_validate_directory,
    )
    guidance = Table.grid(padding=(0, 2))
    guidance.add_column(style="bold cyan", no_wrap=True)
    guidance.add_column(overflow="fold")
    guidance.add_row("Scope", Text("local: project · global: user · all: both + managed resources"))
    guidance.add_row("Resources", Text(", ".join(get_args(DoctorResourceFocus))))
    guidance.add_row("Full reset", Text("all resets whole configuration files and plugin directories", style="yellow"))
    console.print(Panel(guidance, title="Selection guide", border_style="blue"))
    scope = cast(CleanupScope, _prompt_choice(
        label="Scope", default=selection.scope, choices=get_args(CleanupScope),
    ))
    while True:
        resource: str = typer.prompt("Resources", default=selection.resource)
        try:
            resolve_resource_focuses(requested_resources=resource)
            break
        except ValueError as error:
            console.print(Text(f"""Invalid selection: {error}""", style="red"))
    match: str | None = None
    if typer.confirm("Filter by name, command, or source path?", default=selection.match is not None):
        while True:
            match = cast(str, typer.prompt("Match", default=selection.match))
            if match.strip():
                break
            console.print(Text("Enter a nonempty name, command, or source path.", style="red"))
    return CleanupSelection(agent=agent, directory=directory, scope=scope, resource=resource, match=match)


def choose_cleanup_action(*, console: Console, plan: CleanupPlan, backup_root: Path) -> Literal["apply", "revise", "exit"]:
    if plan.blockers:
        console.print(Panel(
            Text("Revise the selection or resolve the errors above before resetting."),
            title="Reset blocked", border_style="red",
        ))
    elif not plan.changes:
        console.print(Panel(Text("Nothing to reset for this selection."), title="No changes", border_style="cyan"))
    else:
        summary = Table.grid(padding=(0, 2))
        summary.add_column(style="bold green", no_wrap=True)
        summary.add_column(overflow="fold")
        summary.add_row("Reset", Text(f"""{len(plan.changes)} path(s)"""))
        summary.add_row("Save originals", Text(str(backup_root)))
        console.print(Panel(summary, title="Ready to reset", border_style="green"))
    choices = ("revise", "exit") if plan.blockers or not plan.changes else ("apply", "revise", "exit")
    console.print(Text("Choose the next action", style="bold cyan"))
    action = cast(Literal["apply", "revise", "exit"], _prompt_choice(
        label="Next action", choices=choices, default="exit",
    ))
    if action == "apply" and not typer.confirm("Apply the displayed reset and preserve backups?", default=False):
        console.print(Text("Reset cancelled. No files changed.", style="yellow"))
        return "exit"
    return action
