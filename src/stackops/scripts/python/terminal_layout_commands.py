from pathlib import Path
from typing import Annotated, Literal

import typer


def list_layouts(
    layouts_file: Annotated[
        Path | None,
        typer.Option("--custom-path", "-p", exists=True, dir_okay=False, help="Layout JSON file. Overrides --source; omit to list layouts from the selected sources."),
    ] = None,
    source: Annotated[
        Literal["workspace", "w", "user", "u", "all", "a"],
        typer.Option("--source", "-s", help="Layout sources: workspace/w, user/u, or all/a. Ignored when --custom-path is provided."),
    ] = "all",
    show_tabs: Annotated[bool, typer.Option("--tabs", "-t", help="Include each tab's name, arrangement, weight, and each pane's name, start directory, and command.")] = False,
    show_stats: Annotated[bool, typer.Option("--stats", "-S", help="Show layout, tab and pane totals, average tabs per layout, and the largest and smallest layouts.")] = False,
) -> None:
    from rich.console import Console
    from rich.table import Table
    from rich.text import Text

    from stackops.scripts.python.helpers.helpers_sessions.sessions_layout_source import resolve_layout_source
    from stackops.utils.schemas.layouts.layout_constants import DEFAULT_TAB_ARRANGEMENT

    try:
        entries = resolve_layout_source(
            ctx=None,
            layouts_file=str(layouts_file) if layouts_file is not None else None,
            source=source,
            test_layout=False,
        )
    except (OSError, ValueError) as error:
        typer.echo(f"""Error: {error}""", err=True)
        raise typer.Exit(code=1) from error

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
        typer.Option("--custom-path", "-p", dir_okay=False, help="Layout JSON file to edit. Overrides --source; omit to choose the user or workspace config file."),
    ] = None,
    source: Annotated[
        Literal["workspace", "w", "user", "u"] | None,
        typer.Option("--source", "-s", help="Config file to edit without prompting. Ignored when --custom-path is provided."),
    ] = None,
    editor: Annotated[
        Literal["hx", "nano", "code"], typer.Option("--editor", "-e", help="Editor to open the layout file with."),
    ] = "hx",
) -> None:
    import shutil
    import subprocess

    from stackops.scripts.python.helpers.helpers_sessions.sessions_layout_source import default_layout_source_paths
    from stackops.scripts.python.terminal_layout_files import resolve_layout_file
    from stackops.utils.managed_file_operations import initialize_managed_file, validate_managed_file
    from stackops.utils.managed_files import get_managed_file_spec

    if layouts_file is not None or source is not None:
        file_path = resolve_layout_file(layouts_file=layouts_file, source=source)
    else:
        source_paths = default_layout_source_paths()
        from stackops.utils.options_utils.options import choose_from_options

        choices = {f"""{name}: {path}""": path for name, path in source_paths.items()}
        selection = choose_from_options(
            options=list(choices), multi=False, custom_input=False, tv=True, msg="Choose a layout config file to edit:",
        )
        if selection is None:
            raise typer.Abort()
        file_path = choices[selection]

    try:
        if file_path.exists() and not file_path.is_file():
            raise ValueError(f"""Layout path is not a file: {file_path}""")
        editor_bin = shutil.which(editor)
        if editor_bin is None:
            raise ValueError(f"""Editor '{editor}' is not available on PATH.""")
        existed = file_path.exists()
        initialize_managed_file(spec=get_managed_file_spec("layouts"), data_path=file_path)
        if not existed:
            typer.echo(f"""Created layout file: {file_path}""")

        editor_command = [editor_bin, "--wait"] if editor == "code" else [editor_bin]
        editor_command.append(str(file_path))
        typer.echo(f"""Editing layout file: {file_path}""")
        result = subprocess.run(editor_command, check=False)
    except (OSError, ValueError) as error:
        typer.echo(f"""Error: {error}""", err=True)
        raise typer.Exit(code=1) from error
    if result.returncode != 0:
        typer.echo(f"""Error: Editor exited with status code {result.returncode}.""", err=True)
        raise typer.Exit(code=result.returncode if result.returncode > 0 else 1)

    try:
        validate_managed_file(kind="layouts", data_path=file_path)
    except (OSError, ValueError) as error:
        typer.echo(f"""Error: Invalid layout file after editing: {error}""", err=True)
        raise typer.Exit(code=1) from error
    typer.echo(f"""Layout file validated: {file_path}""")
