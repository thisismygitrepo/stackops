from collections import Counter
from pathlib import Path

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_interactive import CleanupSelection
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_models import CleanupPlan, CleanupResult
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.models import HookAgent, HookEntry, HookInventory
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorContext, DoctorOrigin


def _display_path(*, path: Path, context: DoctorContext) -> str:
    for root, prefix in ((context.project_root, "."), (context.home_directory, "~")):
        if path.is_relative_to(root):
            relative = path.relative_to(root)
            return prefix if relative == Path(".") else f"""{prefix}/{relative}"""
    return str(path)


def _render_resources(*, console: Console, entries: list[HookEntry], context: DoctorContext) -> None:
    first = entries[0]
    table = Table(
        title=Text(f"""{first.agent} · {first.origin}""", style="bold cyan"),
        box=box.SIMPLE, header_style="bold", expand=True,
    )
    table.add_column("Resource", ratio=2, overflow="fold")
    table.add_column("State / action", ratio=1, overflow="fold")
    table.add_column("Source / command", ratio=3, overflow="fold")
    for entry in entries:
        action = "read-only" if entry.removal is None or entry.origin in ("admin", "system") else entry.removal.action
        resource = Text(entry.name, style="bold")
        resource.append(f"""\n{entry.event}""", style="dim")
        state = Text(entry.state, style="green" if entry.state in ("active", "configured") else "dim")
        state.append(f"""\n{action}""", style="red" if action == "read-only" else "yellow")
        source = Text(_display_path(path=entry.path, context=context), style="cyan")
        if entry.command:
            source.append(f"""\n{entry.command}""", style="dim")
        table.add_row(resource, state, source)
    console.print(table)


def render_cleanup_plan(
    *, console: Console, error_console: Console, plan: CleanupPlan, inventory: HookInventory,
    context: DoctorContext, selection: CleanupSelection, applying: bool, verbose: bool,
) -> None:
    status = "Blocked" if plan.blockers else "Ready" if plan.changes else "Nothing to reset"
    status_style = "red" if plan.blockers else "cyan" if plan.changes else "green"
    overview = Table.grid(padding=(0, 2))
    overview.add_column(style="bold", no_wrap=True)
    overview.add_column(overflow="fold")
    overview.add_row("Status", Text(f"""{status} · {len(plan.entries)} resources · {len(plan.changes)} paths""", style=status_style))
    overview.add_row("Project", Text(str(context.project_root)))
    overview.add_row("Selection", Text(f"""{selection.agent} · {selection.scope} · {selection.resource}"""))
    if selection.match is not None:
        overview.add_row("Match", Text(selection.match))
    if selection.scope != "global" and any(kind.strip().casefold() in ("all", "workspace") for kind in selection.resource.split(",")):
        overview.add_row("Workspace scan", Text("recursive repositories" if selection.recursive else "current repository or direct child repositories"))
    console.print(Panel(overview, title="Depoison · Apply" if applying else "Depoison · Preview", border_style=status_style))

    grouped: dict[tuple[HookAgent, DoctorOrigin], list[HookEntry]] = {}
    for entry in plan.entries:
        grouped.setdefault((entry.agent, entry.origin), []).append(entry)
    if grouped:
        summary = Table(title="Selected resources", box=box.SIMPLE, header_style="bold cyan", expand=True)
        summary.add_column("Agent", style="bold")
        summary.add_column("Scope")
        summary.add_column("Count", justify="right")
        summary.add_column("Resources", overflow="fold", ratio=1)
        for (agent, origin), entries in sorted(grouped.items()):
            counts = Counter(
                entry.event if entry.event in ("workspace", "configuration", "mcp", "plugin", "skill", "instructions") else "hook"
                for entry in entries
            )
            summary.add_row(
                Text(agent), Text(origin), str(len(entries)),
                Text(", ".join(f"""{count} {kind}""" for kind, count in sorted(counts.items()))),
            )
        console.print(summary)

    if plan.changes:
        changes = Table(title="Planned changes", box=box.SIMPLE, header_style="bold cyan", expand=True)
        changes.add_column("Action", style="yellow")
        changes.add_column("Path", overflow="fold", ratio=1)
        for change in sorted(plan.changes, key=lambda item: str(item.snapshot.path)):
            action = "Quarantine" if change.replacement is None else "Edit configuration"
            changes.add_row(action, Text(_display_path(path=change.snapshot.path, context=context)))
        changes.caption = "Quarantine moves the whole file or directory into backup; edits preserve the original in backup."
        console.print(changes)
    elif not plan.blockers:
        console.print("[dim]No matching resources need changes.[/dim]")

    if verbose:
        for _group, entries in sorted(grouped.items()):
            _render_resources(console=console, entries=entries, context=context)
    elif plan.entries:
        console.print("[dim]Use --verbose to show resource names, states, commands, and sources.[/dim]")

    notes: dict[str, None] = {}
    for diagnostic in inventory.diagnostics:
        if selection.scope != "all" and diagnostic.origin != selection.scope:
            continue
        if diagnostic.severity == "error" and f"""{diagnostic.path}: {diagnostic.message}""" in plan.blockers:
            continue
        label = "Notice" if diagnostic.severity == "notice" else "Inspection error covered by whole-source reset"
        path = _display_path(path=diagnostic.path, context=context)
        notes[f"""{label}: {path}: {diagnostic.message}"""] = None
    if notes:
        console.print(Panel(Text("\n".join(notes)), title="Inspection notes", border_style="yellow"))
    if plan.blockers:
        error_console.print(Panel(
            Text("\n".join(f"""• {blocker}""" for blocker in plan.blockers)),
            title="Blocked: reset cannot proceed", border_style="red",
        ))


def render_cleanup_result(*, console: Console, result: CleanupResult) -> None:
    summary = Text(f"""Reset {len(result.changed_paths)} path(s).""", style="bold green")
    if result.backup_directory is not None:
        summary.append("\nOriginals and restore manifest: ", style="default")
        summary.append(str(result.backup_directory), style="cyan")
    if result.changed_paths:
        summary.append("\nRestart the agent to load the reset configuration.", style="default")
    console.print(Panel(summary, title="Reset complete", border_style="green"))
