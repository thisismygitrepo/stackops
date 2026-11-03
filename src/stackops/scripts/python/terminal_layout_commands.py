from pathlib import Path
from typing import Annotated, Literal

import typer


def list_layouts(
    layouts_file: Annotated[
        Path | None,
        typer.Option("--custom-path", "-p", exists=True, dir_okay=False, help="Layout YAML file. Overrides --source; omit to list layouts from the selected sources."),
    ] = None,
    source: Annotated[
        Literal["workspace", "w", "user", "u", "all", "a"],
        typer.Option("--source", "-s", help="Layout sources: workspace/w, user/u, or all/a. Ignored when --custom-path is provided."),
    ] = "all",
    show_tabs: Annotated[bool, typer.Option("--tabs", "-t", help="Include each tab's name, arrangement, weight, and each pane's name, start directory, and command.")] = False,
    show_stats: Annotated[bool, typer.Option("--stats", "-S", help="Show layout, tab and pane totals, average tabs per layout, and the largest and smallest layouts.")] = False,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Print layout metadata as JSON without a picker; --tabs includes pane configuration and --stats includes totals.")] = False,
) -> None:
    import sys
    from contextlib import nullcontext, redirect_stdout

    from rich.console import Console
    from rich.table import Table
    from rich.text import Text

    from stackops.scripts.python.helpers.helpers_sessions.sessions_layout_source import resolve_layout_source
    from stackops.utils.schemas.layouts.layout_constants import DEFAULT_TAB_ARRANGEMENT

    try:
        with redirect_stdout(sys.stderr) if json_output else nullcontext():
            entries = resolve_layout_source(
                ctx=None,
                layouts_file=str(layouts_file) if layouts_file is not None else None,
                source=source,
                test_layout=False,
            )
    except (OSError, ValueError) as error:
        typer.echo(f"""Error: {error}""", err=True)
        raise typer.Exit(code=1) from error

    if json_output:
        import json

        layouts: list[dict[str, object]] = []
        for entry in entries:
            record: dict[str, object] = {
                "selector": entry.selector,
                "name": entry.layout["layoutName"],
                "source_file": str(entry.source_path) if entry.source_path is not None else None,
                "tab_count": len(entry.layout["layoutTabs"]),
                "pane_count": sum(len(tab["panes"]) for tab in entry.layout["layoutTabs"]),
            }
            if show_tabs:
                record["tabs"] = entry.layout["layoutTabs"]
            layouts.append(record)
        payload: dict[str, object] = {"layouts": layouts}
        if show_stats:
            total_tabs = sum(len(entry.layout["layoutTabs"]) for entry in entries)
            payload["stats"] = {
                "layouts": len(entries),
                "tabs": total_tabs,
                "panes": sum(len(tab["panes"]) for entry in entries for tab in entry.layout["layoutTabs"]),
                "average_tabs": total_tabs / len(entries) if entries else 0.0,
                "largest_layout": max(entries, key=lambda entry: len(entry.layout["layoutTabs"])).selector if entries else None,
                "smallest_layout": min(entries, key=lambda entry: len(entry.layout["layoutTabs"])).selector if entries else None,
            }
        typer.echo(json.dumps(payload, ensure_ascii=False))
        return

    table = Table(title=f"""Saved layouts ({len(entries)})""")
    table.add_column("Layout", style="cyan")
    table.add_column("Tabs", justify="right")
    table.add_column("Panes", justify="right")
    table.add_column("Source file")
    for entry in entries:
        table.add_row(
            Text(entry.selector),
            str(len(entry.layout["layoutTabs"])),
            str(sum(len(tab["panes"]) for tab in entry.layout["layoutTabs"])),
            Text(str(entry.source_path)),
        )
    console = Console()
    console.print(table)

    if show_stats:
        total_layouts = len(entries)
        total_tabs = sum(len(entry.layout["layoutTabs"]) for entry in entries)
        total_panes = sum(len(tab["panes"]) for entry in entries for tab in entry.layout["layoutTabs"])
        average_tabs = total_tabs / total_layouts if total_layouts else 0.0
        stats_table = Table(title="Layout statistics")
        stats_table.add_column("Metric")
        stats_table.add_column("Value")
        stats_table.add_row("Layouts", str(total_layouts))
        stats_table.add_row("Tabs", str(total_tabs))
        stats_table.add_row("Panes", str(total_panes))
        stats_table.add_row("Avg tabs/layout", f"""{average_tabs:.2f}""")
        if entries:
            largest = max(entries, key=lambda entry: len(entry.layout["layoutTabs"]))
            smallest = min(entries, key=lambda entry: len(entry.layout["layoutTabs"]))
            stats_table.add_row("Max tabs layout", Text(f"""{largest.selector} ({len(largest.layout["layoutTabs"])})"""))
            stats_table.add_row("Min tabs layout", Text(f"""{smallest.selector} ({len(smallest.layout["layoutTabs"])})"""))
        console.print(stats_table)

    if show_tabs:
        tabs_table = Table(title="Layout tabs")
        tabs_table.add_column("Layout", style="cyan")
        tabs_table.add_column("Tab")
        tabs_table.add_column("Arrangement")
        tabs_table.add_column("Pane")
        tabs_table.add_column("Start directory")
        tabs_table.add_column("Command")
        tabs_table.add_column("Weight", justify="right")
        for entry in entries:
            for tab in entry.layout["layoutTabs"]:
                for pane in tab["panes"]:
                    tabs_table.add_row(
                        Text(entry.selector), Text(tab["tabName"]), Text(tab.get("arrangement", DEFAULT_TAB_ARRANGEMENT) if len(tab["panes"]) > 1 else "—"),
                        Text(pane["paneName"]), Text(pane["startDir"]), Text(pane["command"]),
                        str(tab["tabWeight"]) if "tabWeight" in tab else "—",
                    )
        console.print(tabs_table)


def edit_layouts(
    layouts_file: Annotated[
        Path | None,
        typer.Option("--custom-path", "-p", dir_okay=False, help="Layout YAML file to edit. Overrides --source; omit to choose the user or workspace config file."),
    ] = None,
    source: Annotated[
        Literal["workspace", "w", "user", "u"] | None,
        typer.Option("--source", "-s", help="Config file to edit without prompting. Ignored when --custom-path is provided."),
    ] = None,
    editor: Annotated[
        Literal["hx", "nano", "code"], typer.Option("--editor", "-e", help="Editor to open the layout file with."),
    ] = "hx",
    install_lsp: Annotated[bool, typer.Option("--install-lsp", help="Install the required language server if missing (Helix only).")] = False,
) -> None:
    from stackops.scripts.python.helpers.helpers_sessions.sessions_layout_source import default_layout_source_paths
    from stackops.scripts.python.terminal_layout_files import describe_layout_file, resolve_layout_file
    from stackops.utils.managed_file_cli import run_managed_file_edit

    if layouts_file is not None or source is not None:
        file_path = resolve_layout_file(layouts_file=layouts_file, source=source)
    else:
        source_paths = default_layout_source_paths()
        from stackops.utils.options_utils.options import choose_from_options

        choices = {f"""{name}: {path}  [{describe_layout_file(path=path)}]""": path for name, path in source_paths.items()}
        selection = choose_from_options(
            options=list(choices), multi=False, custom_input=False, tv=True, msg="Choose a layout config file to edit:",
        )
        if selection is None:
            raise typer.Abort()
        file_path = choices[selection]

    run_managed_file_edit(kind="layouts", path=file_path, editor=editor, install_lsp=install_lsp)
