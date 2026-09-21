import platform
from typing import TYPE_CHECKING

import typer

from stackops.scripts.python.helpers.helpers_utils.autostart_common import (
    CATEGORY_LABELS,
    CATEGORY_ORDER,
    CATEGORY_STYLES,
    AutostartCategory,
    AutostartEntry,
    AutostartScope,
)

if TYPE_CHECKING:
    from rich.table import Table


def collect_autostart_entries() -> list[AutostartEntry]:
    system = platform.system()
    match system:
        case "Linux":
            from stackops.scripts.python.helpers.helpers_utils.autostart_linux import collect_linux_entries

            return collect_linux_entries()
        case "Darwin":
            from stackops.scripts.python.helpers.helpers_utils.autostart_macos import collect_macos_entries

            return collect_macos_entries()
        case "Windows":
            from stackops.scripts.python.helpers.helpers_utils.autostart_windows import collect_windows_entries

            return collect_windows_entries()
        case _:
            raise RuntimeError(f"""Autostart inspection is not supported on {system}""")


def build_autostart_table(entries: list[AutostartEntry], show_all: bool) -> "Table":
    from rich import box
    from rich.table import Table

    title = "Auto-start services and programs" if show_all else "Auto-start services and programs (notable)"
    table = Table(title=title, box=box.SIMPLE_HEAVY, header_style="bold cyan", show_lines=False)
    table.add_column("Category", no_wrap=True)
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Description", style="green", overflow="fold")
    table.add_column("Scope", style="yellow", no_wrap=True)
    table.add_column("Source", style="dim", no_wrap=True)
    for category in CATEGORY_ORDER:
        for entry in sorted((item for item in entries if item.category == category), key=lambda item: item.name):
            table.add_row(
                f"[{CATEGORY_STYLES[category]}]{CATEGORY_LABELS[category]}[/]",
                entry.name,
                entry.description or "-",
                entry.scope,
                entry.source,
            )
    return table


def print_autostart_report(
    show_all: bool,
    categories: list[AutostartCategory],
    scope: AutostartScope | None,
    name: str | None,
    source: str | None,
) -> None:
    from rich.console import Console

    entries = collect_autostart_entries()
    if not entries:
        typer.echo("No auto-start entries found")
        return
    name_query = name.casefold() if name is not None else ""
    source_query = source.casefold() if source is not None else ""
    matching = [
        entry for entry in entries
        if (not categories or entry.category in categories)
        and (scope is None or entry.scope == scope)
        and name_query in entry.name.casefold()
        and source_query in entry.source.casefold()
    ]
    visible = [entry for entry in matching if show_all or not entry.stock]
    hidden_count = len(matching) - len(visible)
    console = Console()
    if visible:
        console.print(build_autostart_table(visible, show_all=show_all))
        console.print("[dim]scope 'boot' = system startup; 'login' = user session. Event-triggered entries run when triggered.[/dim]")
    else:
        console.print("No auto-start entries match the filters" if categories or scope or name or source else "No notable auto-start entries found")
    if not show_all and hidden_count:
        console.print(f"[dim]{hidden_count} standard OS services hidden; pass --all to include them.[/dim]")
