"""Summarize a layout file with counts for layouts and tabs."""

from typing import Annotated, cast

import typer


def summarize(
    layout_path: Annotated[str, typer.Argument(..., help="Path to the layout.json file")],
) -> None:
    """Summarize a layout file with counts for layouts and tabs."""
    import json
    from pathlib import Path
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from stackops.utils.files.read import remove_c_style_comments

    console = Console()
    layout_path_obj = Path(layout_path).expanduser().absolute()

    if not layout_path_obj.exists():
        console.print(
            Panel(
                f"❌ Layout file not found:\n{layout_path_obj}",
                title="Error",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)
    if not layout_path_obj.is_file():
        console.print(
            Panel(
                f"❌ Layout path is not a file:\n{layout_path_obj}",
                title="Error",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)

    try:
        json_str = layout_path_obj.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        console.print(
            Panel(
                f"❌ Failed to read layout file:\n{layout_path_obj}\n\n{error}",
                title="Error",
                border_style="red",
            )
        )
        raise typer.Exit(code=1) from error
    try:
        layout_file_obj: object = json.loads(json_str)
    except json.JSONDecodeError:
        try:
            layout_file_obj = json.loads(remove_c_style_comments(json_str))
        except json.JSONDecodeError as error:
            console.print(
                Panel(
                    f"❌ Failed to parse JSON file:\n{layout_path_obj}\n\n{error}",
                    title="Error",
                    border_style="red",
                )
            )
            raise typer.Exit(code=1) from error

    if not isinstance(layout_file_obj, dict):
        console.print(Panel("❌ Layout file root must be a JSON object.", title="Error", border_style="red"))
        raise typer.Exit(code=1)

    layout_file: dict[object, object] = layout_file_obj
    layouts_raw = layout_file.get("layouts")
    if not isinstance(layouts_raw, list):
        console.print(Panel("❌ Missing or invalid 'layouts' array.", title="Error", border_style="red"))
        raise typer.Exit(code=1)

    rows: list[tuple[int, str, int]] = []
    total_tabs = 0
    for index, layout_raw in enumerate(layouts_raw, start=1):
        if not isinstance(layout_raw, dict):
            console.print(Panel(f"❌ Layout #{index} must be a JSON object.", title="Error", border_style="red"))
            raise typer.Exit(code=1)

        layout = cast(dict[object, object], layout_raw)
        layout_name_raw = layout.get("layoutName")
        if layout_name_raw is None:
            layout_name = f"layout#{index}"
        elif isinstance(layout_name_raw, str):
            layout_name = layout_name_raw
        else:
            console.print(Panel(f"❌ Layout #{index} has invalid 'layoutName'.", title="Error", border_style="red"))
            raise typer.Exit(code=1)

        layout_tabs = layout.get("layoutTabs")
        if not isinstance(layout_tabs, list):
            console.print(Panel(f"❌ Layout '{layout_name}' is missing a valid 'layoutTabs' array.", title="Error", border_style="red"))
            raise typer.Exit(code=1)

        tab_count = len(layout_tabs)
        rows.append((index, layout_name, tab_count))
        total_tabs += tab_count

    total_layouts = len(rows)
    avg_tabs = (total_tabs / total_layouts) if total_layouts > 0 else 0.0
    version = str(layout_file.get("version", "unknown"))

    summary_lines = [
        f"[bold]File:[/bold] {layout_path_obj}",
        f"[bold]Version:[/bold] {version}",
        f"[bold]Layouts:[/bold] {total_layouts}",
        f"[bold]Tabs:[/bold] {total_tabs}",
        f"[bold]Avg tabs/layout:[/bold] {avg_tabs:.2f}",
    ]
    if rows:
        max_row = max(rows, key=lambda row: row[2])
        min_row = min(rows, key=lambda row: row[2])
        summary_lines.append(f"[bold]Max tabs layout:[/bold] {max_row[1]} ({max_row[2]})")
        summary_lines.append(f"[bold]Min tabs layout:[/bold] {min_row[1]} ({min_row[2]})")

    console.print(Panel("\n".join(summary_lines), title="[bold blue]Layout Summary[/bold blue]", border_style="blue"))

    table = Table(title=f"[bold cyan]Layouts ({total_layouts})[/bold cyan]")
    table.add_column("#", justify="right")
    table.add_column("Layout Name", style="white")
    table.add_column("Tabs", justify="right", style="green")
    for index, layout_name, tab_count in rows:
        table.add_row(str(index), layout_name, str(tab_count))
    console.print(table)
