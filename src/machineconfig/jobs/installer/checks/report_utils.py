"""
Report Utilities
================

This module provides functionality to generate reports for installed applications.
"""

from typing import Literal, TypedDict

from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.style import Style
from rich.table import Table
from rich.text import Text

from machineconfig.jobs.installer.checks.vt_utils import ScanResult

console = Console()

APP_METADATA_KEYS: tuple[str, ...] = (
    "app_name",
    "version",
    "scan_time",
    "app_path",
    "app_url",
    "scan_summary_available",
    "notes",
)
ENGINE_REPORT_KEYS: tuple[str, ...] = (
    "app_name",
    "engine_name",
    "engine_category",
    "engine_result",
)


class AppMetadataRow(TypedDict):
    app_name: str
    version: str | None
    scan_time: str
    app_path: str
    app_url: str
    scan_summary_available: bool
    notes: str


class AppData(TypedDict):
    app_name: str
    version: str | None
    positive_pct: float | None
    flagged_engines: int
    verdict_engines: int
    total_engines: int
    malicious_engines: int
    suspicious_engines: int
    harmless_engines: int
    undetected_engines: int
    unsupported_engines: int
    timeout_engines: int
    failure_engines: int
    other_engines: int
    notes: str
    scan_time: str
    app_path: str
    app_url: str


class EngineReportRow(TypedDict):
    app_name: str
    version: str | None
    scan_time: str
    app_path: str
    app_url: str
    engine_name: str
    engine_category: str
    engine_result: str | None


class StoredEngineReportRow(TypedDict):
    app_name: str
    engine_name: str
    engine_category: str
    engine_result: str | None


class ScannedAppRecord(TypedDict):
    app_data: AppData
    engine_results: list[StoredEngineReportRow]


class ReportSummary(TypedDict):
    total_apps: int
    clean_apps: int
    review_apps: int
    flagged_apps: int
    no_verdict_apps: int
    pending_apps: int
    total_engines: int
    verdict_engines: int
    flagged_engines: int


def build_app_metadata_row(app_data: AppData) -> AppMetadataRow:
    return {
        "app_name": app_data["app_name"],
        "version": app_data["version"],
        "scan_time": app_data["scan_time"],
        "app_path": app_data["app_path"],
        "app_url": app_data["app_url"],
        "scan_summary_available": app_data["positive_pct"] is not None,
        "notes": app_data["notes"],
    }


def build_engine_report_rows(app_data: AppData, scan_results: list[ScanResult]) -> list[StoredEngineReportRow]:
    return [
        {
            "app_name": app_data["app_name"],
            "engine_name": scan_result["engine_name"],
            "engine_category": scan_result["category"],
            "engine_result": scan_result["result"],
        }
        for scan_result in scan_results
    ]


def _build_app_name_cell(app_name: str, app_url: str) -> Text:
    if not app_url:
        return Text(app_name, style="bold white")
    return Text(app_name, style=Style(color="cyan", underline=True, link=app_url))


def _build_verdict_ratio(row: AppData) -> str:
    if row["verdict_engines"] == 0 and row["total_engines"] == 0:
        return "0/0"
    return f"{row['flagged_engines']}/{row['verdict_engines']}"


def _get_row_status(row: AppData) -> Literal["pending", "no_verdict", "clean", "review", "flagged"]:
    if row["positive_pct"] is None:
        return "pending"
    if row["verdict_engines"] == 0:
        return "no_verdict"
    if row["positive_pct"] == 0.0:
        return "clean"
    if row["positive_pct"] < 5.0:
        return "review"
    return "flagged"


def _build_safety_label(row: AppData) -> str:
    match _get_row_status(row):
        case "pending":
            return "Pending"
        case "no_verdict":
            return f"No verdicts ({row['total_engines']} engines)"
        case "clean":
            return f"Clean {_build_verdict_ratio(row)} ({row['positive_pct']:.1f}%)"
        case "review":
            return f"Review {_build_verdict_ratio(row)} ({row['positive_pct']:.1f}%)"
        case "flagged":
            return f"Flagged {_build_verdict_ratio(row)} ({row['positive_pct']:.1f}%)"


def _build_safety_cell(row: AppData) -> Text:
    match _get_row_status(row):
        case "pending":
            return Text(_build_safety_label(row), style="bold yellow")
        case "no_verdict":
            return Text(_build_safety_label(row), style="bold yellow")
        case "clean":
            return Text(_build_safety_label(row), style="bold green")
        case "review":
            return Text(_build_safety_label(row), style="bold yellow")
        case "flagged":
            return Text(_build_safety_label(row), style="bold red")


def _build_latest_scan_border_style(row: AppData) -> str:
    match _get_row_status(row):
        case "pending":
            return "yellow"
        case "no_verdict":
            return "yellow"
        case "clean":
            return "green"
        case "review":
            return "yellow"
        case "flagged":
            return "red"


def _build_verdicts_cell(row: AppData) -> Text:
    if row["total_engines"] == 0:
        return Text("-", style="dim")
    verdict_text = f"{row['verdict_engines']}/{row['total_engines']}"
    if row["verdict_engines"] == row["total_engines"]:
        return Text(verdict_text, style="bold cyan")
    return Text(verdict_text, style="bold yellow")


def _build_breakdown_cell(row: AppData) -> Text:
    return Text(
        f"M:{row['malicious_engines']} S:{row['suspicious_engines']} H:{row['harmless_engines']} U:{row['undetected_engines']}",
        style="dim",
    )


def _build_notes_cell(notes: str) -> Text:
    if not notes:
        return Text("-", style="dim")
    if notes == "All reporting engines returned a verdict.":
        return Text(notes, style="dim")
    return Text(notes, style="yellow")


def _build_engine_category_cell(category: str) -> Text:
    match category:
        case "malicious":
            return Text(category, style="bold red")
        case "suspicious":
            return Text(category, style="bold yellow")
        case "harmless":
            return Text(category, style="bold green")
        case "undetected":
            return Text(category, style="dim")
        case "timeout" | "confirmed-timeout" | "type-unsupported":
            return Text(category, style="yellow")
        case "failure":
            return Text(category, style="red")
        case _:
            return Text(category, style="dim")


def _build_engine_result_cell(result: str | None) -> Text:
    if result is None:
        return Text("-", style="dim")
    return Text(result, overflow="ellipsis")


def _summarize_report(data: list[AppData]) -> ReportSummary:
    summary: ReportSummary = {
        "total_apps": len(data),
        "clean_apps": 0,
        "review_apps": 0,
        "flagged_apps": 0,
        "no_verdict_apps": 0,
        "pending_apps": 0,
        "total_engines": 0,
        "verdict_engines": 0,
        "flagged_engines": 0,
    }
    for row in data:
        match _get_row_status(row):
            case "pending":
                summary["pending_apps"] += 1
            case "no_verdict":
                summary["no_verdict_apps"] += 1
            case "clean":
                summary["clean_apps"] += 1
            case "review":
                summary["review_apps"] += 1
            case "flagged":
                summary["flagged_apps"] += 1
        summary["total_engines"] += row["total_engines"]
        summary["verdict_engines"] += row["verdict_engines"]
        summary["flagged_engines"] += row["flagged_engines"]
    return summary


def build_latest_scan_panel(last_scanned: AppData | None, completed_count: int, total_count: int) -> Panel:
    subtitle = f"{completed_count}/{total_count} complete"
    if last_scanned is None:
        return Panel(Text("Waiting for the first completed scan...", style="dim"), title="Latest Scan Result", subtitle=subtitle, border_style="blue", expand=False)

    details = Table.grid(padding=(0, 1), expand=False)
    details.add_column(style="bold cyan", justify="right", no_wrap=True)
    details.add_column(overflow="ellipsis", max_width=96)
    details.add_row("App", _build_app_name_cell(last_scanned["app_name"], last_scanned["app_url"]))
    details.add_row("Version", Text(last_scanned["version"] or "-"))
    details.add_row("Safety", _build_safety_cell(last_scanned))
    details.add_row("Verdicts", _build_verdicts_cell(last_scanned))
    details.add_row("Breakdown", _build_breakdown_cell(last_scanned))
    details.add_row("Notes", _build_notes_cell(last_scanned["notes"]))
    details.add_row("Scanned", Text(last_scanned["scan_time"], style="dim"))
    if last_scanned["app_url"]:
        upload_state = Text("Open uploaded copy", style=Style(color="cyan", underline=True, link=last_scanned["app_url"]))
    else:
        upload_state = Text("Upload unavailable", style="bold red")
    details.add_row("Upload", upload_state)
    details.add_row("Path", Text(last_scanned["app_path"], style="dim"))

    return Panel(details, title="Latest Scan Result", subtitle=subtitle, border_style=_build_latest_scan_border_style(last_scanned), expand=False)


def _build_report_overview_panel(data: list[AppData]) -> Panel:
    summary = _summarize_report(data)
    overview = Text.assemble(
        ("apps ", "bold cyan"),
        (str(summary["total_apps"]), "bold white"),
        (" | clean ", "bold green"),
        (str(summary["clean_apps"]), "bold white"),
        (" | review ", "bold yellow"),
        (str(summary["review_apps"]), "bold white"),
        (" | flagged ", "bold red"),
        (str(summary["flagged_apps"]), "bold white"),
        (" | no verdict ", "bold yellow"),
        (str(summary["no_verdict_apps"]), "bold white"),
        (" | pending ", "bold yellow"),
        (str(summary["pending_apps"]), "bold white"),
        (" | engines ", "bold cyan"),
        (str(summary["total_engines"]), "bold white"),
        (" | verdicts ", "bold cyan"),
        (str(summary["verdict_engines"]), "bold white"),
        (" | flagged engines ", "bold red"),
        (str(summary["flagged_engines"]), "bold white"),
    )
    return Panel(overview, title="Scan Overview", border_style="cyan", expand=False)


def _build_rich_table(data: list[AppData]) -> Table:
    table = Table(
        title="Safety Report Summary",
        box=box.ROUNDED,
        header_style="bold cyan",
        row_styles=["", "dim"],
        expand=False,
    )
    table.add_column("App", no_wrap=True)
    table.add_column("Ver", style="cyan", no_wrap=True)
    table.add_column("Safety", no_wrap=True)
    table.add_column("Verdicts", no_wrap=True)
    table.add_column("Breakdown", no_wrap=True)
    table.add_column("Notes", overflow="ellipsis", max_width=44)
    table.add_column("Path", overflow="ellipsis", max_width=36)

    for row in data:
        table.add_row(
            _build_app_name_cell(row["app_name"], row["app_url"]),
            row["version"] or "-",
            _build_safety_cell(row),
            _build_verdicts_cell(row),
            _build_breakdown_cell(row),
            _build_notes_cell(row["notes"]),
            row["app_path"],
        )
    return table


def build_summary_group(data: list[AppData]) -> Group:
    return Group(_build_report_overview_panel(data), _build_rich_table(data))


def build_engine_results_table(data: list[EngineReportRow]) -> Table:
    table = Table(
        title="Engine Results",
        box=box.ROUNDED,
        header_style="bold cyan",
        row_styles=["", "dim"],
        expand=False,
    )
    table.add_column("App", no_wrap=True)
    table.add_column("Ver", style="cyan", no_wrap=True)
    table.add_column("Engine", no_wrap=True)
    table.add_column("Category", no_wrap=True)
    table.add_column("Result", overflow="ellipsis", max_width=44)
    table.add_column("Scanned", no_wrap=True)
    table.add_column("Path", overflow="ellipsis", max_width=36)

    for row in data:
        table.add_row(
            _build_app_name_cell(row["app_name"], row["app_url"]),
            row["version"] or "-",
            row["engine_name"],
            _build_engine_category_cell(row["engine_category"]),
            _build_engine_result_cell(row["engine_result"]),
            Text(row["scan_time"], style="dim"),
            row["app_path"],
        )
    return table
