import subprocess
import sys
from pathlib import Path
from typing import Annotated

import typer

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_models import CleanupScope


def depoison(
    agent: Annotated[str, typer.Argument(help="Agent to reset, or all.")] = "all",
    directory: Annotated[Path | None, typer.Option("--directory", "-d", exists=True, file_okay=False, help="Inspect this project directory.")] = None,
    scope: Annotated[CleanupScope, typer.Option("--scope", "-s", help="Select local, global, or all configuration.")] = "all",
    resource: Annotated[str, typer.Option("--resource", "-r", help="Comma-separated resources: all, hook, plugin, mcp, skill, instructions, configuration.")] = "all",
    match: Annotated[str | None, typer.Option("--match", "-m", help="Select resources by name, command, or source path substring.")] = None,
    apply: Annotated[bool, typer.Option("--apply", "-a", help="Apply the displayed reset and keep original files in quarantine.")] = False,
) -> None:
    """Preview or reset hooks, plugins, MCP servers, skills, instructions, and configuration."""
    from stackops.utils.meta import lambda_to_python_script

    worker_source = lambda_to_python_script(
        lambda: _run_depoison(
            agent=agent,
            directory=str(directory if directory is not None else Path.cwd()),
            scope=scope,
            resource=resource,
            match=match,
            apply=apply,
        ),
        in_global=True,
        import_module=False,
    )
    result = subprocess.run(
        ["uv", "run", "--no-project", "--python", sys.executable, "--with", "tomlkit", "python", "-c", worker_source],
        check=False,
    )
    raise typer.Exit(code=result.returncode)


def _run_depoison(*, agent: str, directory: str, scope: CleanupScope, resource: str, match: str | None, apply: bool) -> None:
    from pathlib import Path

    import typer

    from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_apply import apply_cleanup_plan
    from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_plan import build_cleanup_plan
    from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_resources import collect_cleanup_resources
    from stackops.scripts.python.helpers.helpers_agents.agents_doctor.command import resolve_resource_focuses
    from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.discovery import collect_hooks
    from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.models import HookInventory
    from stackops.scripts.python.helpers.helpers_agents.agents_doctor.registry import resolve_doctor_definitions
    from stackops.scripts.python.helpers.helpers_agents.agents_doctor.scanning import create_doctor_context

    try:
        context = create_doctor_context(working_directory=Path(directory))
        definitions = resolve_doctor_definitions(requested_agent=agent)
        focuses = resolve_resource_focuses(requested_resources=resource)
        inventories: list[HookInventory] = []
        for definition in definitions:
            if "all" in focuses or "hook" in focuses:
                inventories.append(collect_hooks(agent=definition.agent, context=context))
            if focuses != ("hook",):
                inventories.append(collect_cleanup_resources(agent=definition.agent, context=context, resource_focuses=focuses))
        inventory = HookInventory(
            entries=tuple(entry for item in inventories for entry in item.entries),
            diagnostics=tuple(diagnostic for item in inventories for diagnostic in item.diagnostics),
        )
        plan = build_cleanup_plan(inventory=inventory, scope=scope, match=match, home_directory=context.home_directory)
        typer.echo(f"{'Apply' if apply else 'Preview'}: {len(plan.entries)} resource(s), {len(plan.changes)} path(s).")
        for entry in plan.entries:
            action = "read-only" if entry.removal is None else entry.removal.action
            typer.echo(f"  {entry.agent} {entry.origin}: {entry.name} — {action} — {entry.path}")
            if entry.command:
                typer.echo(f"    {entry.command}")
        for change in plan.changes:
            action = "quarantine" if change.replacement is None else "edit configuration"
            typer.echo(f"  Will {action}: {change.snapshot.path}")
        for diagnostic in inventory.diagnostics:
            if scope != "all" and diagnostic.origin != scope:
                continue
            if diagnostic.severity == "notice":
                typer.echo(f"Notice: {diagnostic.path}: {diagnostic.message}")
            elif f"{diagnostic.path}: {diagnostic.message}" not in plan.blockers:
                typer.echo(f"Inspection error covered by whole-source reset: {diagnostic.path}: {diagnostic.message}")
        for blocker in plan.blockers:
            typer.echo(f"Blocked: {blocker}", err=True)
        if plan.blockers:
            raise SystemExit(1)
        if not apply:
            typer.echo("Preview only. Add --apply to perform this reset and preserve backups.")
            raise SystemExit(0)
        result = apply_cleanup_plan(
            plan=plan,
            backup_root=context.home_directory / ".local" / "state" / "stackops" / "depoison",
            home_directory=context.home_directory,
        )
        typer.echo(f"Reset {len(result.changed_paths)} path(s).")
        if result.backup_directory is not None:
            typer.echo(f"Originals and restore manifest: {result.backup_directory}")
        if result.changed_paths:
            typer.echo("Restart the agent to load the reset configuration.")
    except (OSError, ValueError) as error:
        typer.echo(f"""Error: {error}""", err=True)
        raise SystemExit(2) from error
