"""
Report Utilities
================

This module provides functionality to generate reports for installed applications.
"""

from pathlib import Path
from typing import TypedDict

from rich.console import Console
from rich import box
from rich.style import Style
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()

REPORT_KEYS: tuple[str, ...] = ("app_name", "version", "positive_pct", "scan_time", "app_path", "app_url")
REPORT_HEADERS: dict[str, str] = {
    "app_name": "App",
    "version": "Version",
    "positive_pct": "Positives",
    "scan_time": "Scanned",
    "app_path": "Path",
    "app_url": "Upload",
}

class AppData(TypedDict):
    app_name: str
    version: str | None
    positive_pct: float | None
    scan_time: str
    app_path: str
    app_url: str


def _format_markdown_value(key: str, value: object) -> str:
    if value is None:
        return ""
    if key == "positive_pct":
        if isinstance(value, int | float):
            return f"{float(value):.1f}%"
        return ""
    return str(value)


def _build_app_name_cell(app_name: str, app_url: str) -> Text:
    if not app_url:
        return Text(app_name, style="bold white")
    return Text(app_name, style=Style(color="cyan", underline=True, link=app_url))


def _build_safety_cell(positive_pct: float | None) -> Text:
    if positive_pct is None:
        return Text("Pending", style="bold yellow")
    if positive_pct == 0.0:
        return Text("Clean 0.0%", style="bold green")
    if positive_pct < 5.0:
        return Text(f"Review {positive_pct:.1f}%", style="bold yellow")
    return Text(f"Flagged {positive_pct:.1f}%", style="bold red")


def _build_latest_scan_border_style(positive_pct: float | None) -> str:
    if positive_pct is None:
        return "yellow"
    if positive_pct == 0.0:
        return "green"
    if positive_pct < 5.0:
        return "yellow"
    return "red"


def build_latest_scan_panel(last_scanned: AppData | None, completed_count: int, total_count: int) -> Panel:
    subtitle = f"{completed_count}/{total_count} complete"
    if last_scanned is None:
        return Panel(Text("Waiting for the first completed scan...", style="dim"), title="Latest Scan Result", subtitle=subtitle, border_style="blue", expand=False)

    details = Table.grid(padding=(0, 1), expand=False)
    details.add_column(style="bold cyan", justify="right", no_wrap=True)
    details.add_column(overflow="ellipsis", max_width=96)
    details.add_row("App", _build_app_name_cell(last_scanned["app_name"], last_scanned["app_url"]))
    details.add_row("Version", Text(last_scanned["version"] or "-"))
    details.add_row("Safety", _build_safety_cell(last_scanned["positive_pct"]))
    details.add_row("Scanned", Text(last_scanned["scan_time"], style="dim"))
    if last_scanned["app_url"]:
        upload_state = Text("Open uploaded copy", style=Style(color="cyan", underline=True, link=last_scanned["app_url"]))
    else:
        upload_state = Text("Upload unavailable", style="bold red")
    details.add_row("Upload", upload_state)
    details.add_row("Path", Text(last_scanned["app_path"], style="dim"))

    return Panel(
        details,
        title="Latest Scan Result",
        subtitle=subtitle,
        border_style=_build_latest_scan_border_style(last_scanned["positive_pct"]),
        expand=False,
    )


def _build_rich_table(data: list[AppData]) -> Table:
    clean_count = sum(1 for row in data if row["positive_pct"] == 0.0)
    pending_count = sum(1 for row in data if row["positive_pct"] is None)
    flagged_count = sum(1 for row in data if row["positive_pct"] not in {None, 0.0})

    table = Table(
        title="Safety Report Summary",
        caption=f"apps: {len(data)} | clean: {clean_count} | flagged: {flagged_count} | pending: {pending_count}",
        box=box.ROUNDED,
        header_style="bold cyan",
        row_styles=["", "dim"],
        expand=False,
    )
    table.add_column("App", no_wrap=True)
    table.add_column("Ver", style="cyan", no_wrap=True)
    table.add_column("Safety", no_wrap=True)
    table.add_column("Scanned", style="dim", no_wrap=True)
    table.add_column("Path", overflow="ellipsis", no_wrap=True, max_width=36)

    for row in data:
        version = row["version"] if row["version"] else "-"
        table.add_row(
            _build_app_name_cell(row["app_name"], row["app_url"]),
            version,
            _build_safety_cell(row["positive_pct"]),
            row["scan_time"],
            row["app_path"],
        )
    return table


def generate_markdown_report(data: list[AppData], output_path: Path) -> None:
    """Generates a Markdown table from the app data."""
    if not data:
        return

    header = "| " + " | ".join(REPORT_HEADERS[key] for key in REPORT_KEYS) + " |"
    separator = "| " + " | ".join("---" for _ in REPORT_KEYS) + " |"
    rows = []
    for row in data:
        row_values = [_format_markdown_value(key, row[key]) for key in REPORT_KEYS]
        rows.append("| " + " | ".join(row_values) + " |")

    content = "\n".join([header, separator] + rows)
    output_path.write_text(content, encoding="utf-8")
    console.print(_build_rich_table(data))
