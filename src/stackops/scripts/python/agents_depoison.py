import subprocess
import sys
from pathlib import Path
from typing import Annotated

import typer

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_models import CleanupScope


def depoison(
    agent: Annotated[str, typer.Argument(help="Agent to reset, or all.")] = "all",
    directory: Annotated[Path | None, typer.Option("--directory", "-d", exists=True, file_okay=False, help="Inspect a project or a directory containing repositories.")] = None,
    scope: Annotated[CleanupScope, typer.Option("--scope", "-s", help="Select local, global, or all resources. Workspace folders are local.")] = "all",
    resource: Annotated[str, typer.Option("--resource", "-r", help="Comma-separated resources: all, workspace (.ai folders), hook, plugin, mcp, skill, instructions, configuration.")] = "all",
    recursive: Annotated[bool, typer.Option("--recursive", "-R", help="Recurse into nested repositories when collecting .ai folders.")] = False,
    match: Annotated[str | None, typer.Option("--match", "-m", help="Select resources by name, command, or source path substring.")] = None,
    apply: Annotated[bool, typer.Option("--apply", "-a", help="Apply the displayed reset and keep original files in quarantine.")] = False,
    interactive: Annotated[
        bool, typer.Option("--interactive", "-i", help="Choose targets, inspect status, and confirm a reset step by step (even with --apply).")
    ] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Show every resource, state, command, and source path.")] = False,
    tui: Annotated[
        bool, typer.Option("--tui", "-t", help="Browse resources and select resets in a terminal app; always confirm before applying, even with --apply.")
    ] = False,
) -> None:
    if tui:
        from stackops.scripts.python.helpers.helpers_agents.agents_doctor.tui_launch import launch_agent_tui

        launch_agent_tui(
            mode="depoison", agent=agent, directory=str(directory if directory is not None else Path.cwd()),
            resource=resource, scope=scope, match=match, recursive=recursive,
        )
        return
    from stackops.utils.meta import lambda_to_python_script

    worker_source = lambda_to_python_script(
        lambda: _run_depoison(
            agent=agent,
            directory=str(directory if directory is not None else Path.cwd()),
            scope=scope,
            resource=resource,
            recursive=recursive,
            match=match,
            apply=apply,
            interactive=interactive,
            verbose=verbose,
        ),
        in_global=True,
        import_module=False,
    )
    result = subprocess.run(
        ["uv", "run", "--no-project", "--python", sys.executable, "--with", "tomlkit", "python", "-c", worker_source],
        check=False,
    )
    raise typer.Exit(code=result.returncode)


def _run_depoison(
    *, agent: str, directory: str, scope: CleanupScope, resource: str, recursive: bool,
    match: str | None, apply: bool, interactive: bool, verbose: bool,
) -> None:
    from pathlib import Path

    import typer
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text

    from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_apply import apply_cleanup_plan
    from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_interactive import (
        CleanupSelection,
        choose_cleanup_action,
        prompt_cleanup_selection,
    )
    from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_output import render_cleanup_plan, render_cleanup_result
    from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_plan import build_cleanup_plan
    from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_resources import collect_cleanup_resources
    from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_workspace import collect_workspace_resources, resolve_cleanup_resources
    from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.discovery import collect_hooks
    from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.models import HookInventory
    from stackops.scripts.python.helpers.helpers_agents.agents_doctor.registry import resolve_doctor_definitions
    from stackops.scripts.python.helpers.helpers_agents.agents_doctor.scanning import create_doctor_context

    console = Console()
    error_console = Console(stderr=True)
    try:
        selection = CleanupSelection(agent=agent, directory=directory, scope=scope, resource=resource, match=match, recursive=recursive)
        while True:
            if interactive:
                selection = prompt_cleanup_selection(selection=selection, console=console)
                console.rule("Step 2/4 · Inspect current resources", style="cyan")
            context = create_doctor_context(working_directory=Path(selection.directory))
            definitions = resolve_doctor_definitions(requested_agent=selection.agent)
            focuses, include_workspace = resolve_cleanup_resources(requested_resources=selection.resource)
            with console.status("Inspecting resources...") as status:
                inventories: list[HookInventory] = []
                for definition in definitions:
                    status.update(Text(f"""Inspecting {definition.display_name}..."""))
                    if "all" in focuses or "hook" in focuses:
                        inventories.append(collect_hooks(agent=definition.agent, context=context))
                    if focuses and focuses != ("hook",):
                        inventories.append(collect_cleanup_resources(agent=definition.agent, context=context, resource_focuses=focuses))
                if include_workspace and selection.scope != "global":
                    status.update("Inspecting repository .ai folders...")
                    inventories.append(collect_workspace_resources(context=context, recursive=selection.recursive))
                inventory = HookInventory(
                    entries=tuple(entry for item in inventories for entry in item.entries),
                    diagnostics=tuple(diagnostic for item in inventories for diagnostic in item.diagnostics),
                )
                status.update("Building reset plan...")
                plan = build_cleanup_plan(inventory=inventory, scope=selection.scope, match=selection.match, home_directory=context.home_directory)
            if interactive:
                console.rule("Step 3/4 · Review the reset plan", style="cyan")
            render_cleanup_plan(
                console=console, error_console=error_console, plan=plan, inventory=inventory,
                context=context, selection=selection, applying=apply and not interactive, verbose=verbose,
            )
            if interactive:
                action = choose_cleanup_action(
                    plan=plan, backup_root=context.home_directory / ".local" / "state" / "stackops" / "depoison", console=console,
                )
                if action == "revise":
                    continue
                if action == "exit":
                    console.rule("Step 4/4 · Finished", style="cyan")
                    console.print("[dim]No files changed.[/dim]")
                    raise SystemExit(1 if plan.blockers else 0)
                console.rule("Step 4/4 · Back up originals and apply", style="cyan")
            elif plan.blockers:
                raise SystemExit(1)
            elif not apply:
                if plan.changes:
                    console.print(Panel(
                        "Preview only. Add [bold]--apply[/bold] to perform this reset and preserve backups.",
                        title="Next step", border_style="cyan",
                    ))
                raise SystemExit(0)
            break
        result = apply_cleanup_plan(
            plan=plan,
            backup_root=context.home_directory / ".local" / "state" / "stackops" / "depoison",
            home_directory=context.home_directory,
        )
        render_cleanup_result(console=console, result=result)
    except (typer.Abort, KeyboardInterrupt) as error:
        error_console.print("[yellow]Cancelled.[/yellow]")
        raise SystemExit(1) from error
    except (OSError, ValueError) as error:
        error_console.print(Panel(Text(str(error)), title="Error: reset failed", border_style="red"))
        raise SystemExit(2) from error
