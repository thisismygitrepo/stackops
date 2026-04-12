import csv
from io import StringIO
from pathlib import Path
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Literal

from machineconfig.jobs.installer.checks.vt_utils import summarize_scan_results

if TYPE_CHECKING:
    from rich.table import Table

    from machineconfig.jobs.installer.checks.report_utils import AppData, AppMetadataRow, EngineReportRow, StoredEngineReportRow


ReportFormat = Literal["table", "csv"]
ReportView = Literal["engines", "app-summary", "apps", "options", "stats"]


def _parse_positive_pct(value: str | None) -> float | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned or cleaned.lower() == "none":
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    cleaned = str(value).strip().lower()
    return cleaned in {"1", "true", "yes", "y"}


def normalize_app_names(app_names: list[str] | None) -> set[str] | None:
    if app_names is None:
        return None
    return {app_name.strip().lower() for app_name in app_names if app_name.strip()}


def parse_apps_argument(apps: str | None) -> list[str] | None:
    if apps is None:
        return None
    app_names = [name.strip() for name in apps.split(",") if name.strip()]
    return app_names or None


def to_app_metadata_list(rows: Sequence[Mapping[str, object]]) -> list[AppMetadataRow]:
    app_data_list: list[AppMetadataRow] = []
    for row in rows:
        app_name = str(row.get("app_name", ""))
        version_raw = row.get("version")
        version = str(version_raw) if version_raw not in {None, ""} else None
        scan_time = str(row.get("scan_time", ""))
        app_path = str(row.get("app_path", ""))
        app_url = str(row.get("app_url", ""))
        notes = str(row.get("notes", ""))
        scan_summary_available_raw = row.get("scan_summary_available")
        scan_summary_available = (
            _parse_bool(scan_summary_available_raw)
            if scan_summary_available_raw is not None
            else _parse_positive_pct(str(row.get("positive_pct", ""))) is not None
        )
        app_data_list.append(
            {
                "app_name": app_name,
                "version": version,
                "scan_time": scan_time,
                "app_path": app_path,
                "app_url": app_url,
                "scan_summary_available": scan_summary_available,
                "notes": notes,
            }
        )
    return app_data_list


def to_engine_report_rows(rows: Sequence[Mapping[str, object]]) -> list[StoredEngineReportRow]:
    engine_rows: list[StoredEngineReportRow] = []
    for row in rows:
        engine_result_raw = row.get("engine_result")
        engine_result = None if engine_result_raw in {None, ""} else str(engine_result_raw)
        engine_rows.append(
            {
                "app_name": str(row.get("app_name", "")),
                "engine_name": str(row.get("engine_name", "")),
                "engine_category": str(row.get("engine_category", "")),
                "engine_result": engine_result,
            }
        )
    return engine_rows


def _build_empty_app_data(app_row: AppMetadataRow) -> AppData:
    return {
        "app_name": app_row["app_name"],
        "version": app_row["version"],
        "positive_pct": None,
        "flagged_engines": 0,
        "verdict_engines": 0,
        "total_engines": 0,
        "malicious_engines": 0,
        "suspicious_engines": 0,
        "harmless_engines": 0,
        "undetected_engines": 0,
        "unsupported_engines": 0,
        "timeout_engines": 0,
        "failure_engines": 0,
        "other_engines": 0,
        "notes": app_row["notes"],
        "scan_time": app_row["scan_time"],
        "app_path": app_row["app_path"],
        "app_url": app_row["app_url"],
    }


def build_app_data_list(app_rows: Sequence[AppMetadataRow], engine_rows: Sequence[StoredEngineReportRow]) -> list[AppData]:
    engine_rows_by_app: dict[str, list[StoredEngineReportRow]] = {}
    for engine_row in engine_rows:
        engine_rows_by_app.setdefault(engine_row["app_name"], []).append(engine_row)

    app_data_list: list[AppData] = []
    for app_row in app_rows:
        app_data = _build_empty_app_data(app_row)
        if app_row["scan_summary_available"]:
            scan_summary = summarize_scan_results(
                [
                    {"engine_name": engine_row["engine_name"], "category": engine_row["engine_category"], "result": engine_row["engine_result"]}
                    for engine_row in engine_rows_by_app.get(app_row["app_name"], [])
                ]
            )
            app_data["positive_pct"] = scan_summary["positive_pct"]
            app_data["flagged_engines"] = scan_summary["flagged_engines"]
            app_data["verdict_engines"] = scan_summary["verdict_engines"]
            app_data["total_engines"] = scan_summary["total_engines"]
            app_data["malicious_engines"] = scan_summary["malicious_engines"]
            app_data["suspicious_engines"] = scan_summary["suspicious_engines"]
            app_data["harmless_engines"] = scan_summary["harmless_engines"]
            app_data["undetected_engines"] = scan_summary["undetected_engines"]
            app_data["unsupported_engines"] = scan_summary["unsupported_engines"]
            app_data["timeout_engines"] = scan_summary["timeout_engines"]
            app_data["failure_engines"] = scan_summary["failure_engines"]
            app_data["other_engines"] = scan_summary["other_engines"]
            app_data["notes"] = scan_summary["notes"]
        app_data_list.append(app_data)
    return app_data_list


def hydrate_engine_report_rows(app_rows: Sequence[AppMetadataRow], engine_rows: Sequence[StoredEngineReportRow]) -> list[EngineReportRow]:
    app_rows_by_name = {app_row["app_name"]: app_row for app_row in app_rows}
    hydrated_engine_rows: list[EngineReportRow] = []
    for engine_row in engine_rows:
        app_row = app_rows_by_name.get(engine_row["app_name"])
        hydrated_engine_rows.append(
            {
                "app_name": engine_row["app_name"],
                "version": app_row["version"] if app_row is not None else None,
                "scan_time": app_row["scan_time"] if app_row is not None else "",
                "app_path": app_row["app_path"] if app_row is not None else "",
                "app_url": app_row["app_url"] if app_row is not None else "",
                "engine_name": engine_row["engine_name"],
                "engine_category": engine_row["engine_category"],
                "engine_result": engine_row["engine_result"],
            }
        )
    return hydrated_engine_rows


def _filter_app_metadata_rows(app_rows: list[AppMetadataRow], app_names: set[str] | None) -> list[AppMetadataRow]:
    if app_names is None:
        return app_rows
    return [row for row in app_rows if row["app_name"].lower() in app_names]


def _filter_stored_engine_rows(engine_rows: list[StoredEngineReportRow], app_names: set[str] | None) -> list[StoredEngineReportRow]:
    if app_names is None:
        return engine_rows
    return [row for row in engine_rows if row["app_name"].lower() in app_names]


def _stringify_report_value(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def render_csv_text(rows: Sequence[Mapping[str, object]], columns: Sequence[str]) -> str:
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(columns))
    writer.writeheader()
    for row in rows:
        writer.writerow({column: _stringify_report_value(row.get(column)) for column in columns})
    return buffer.getvalue().rstrip()


def build_raw_csv_table(title: str, rows: Sequence[Mapping[str, object]], columns: Sequence[str]) -> Table:
    from rich import box
    from rich.table import Table

    table = Table(title=title, box=box.ROUNDED, header_style="bold cyan", row_styles=["", "dim"], expand=False)
    for column in columns:
        table.add_column(column, overflow="ellipsis", max_width=44)
    for row in rows:
        table.add_row(*[_stringify_report_value(row.get(column)) for column in columns])
    return table


def load_filtered_report_rows(
    normalized_app_names: set[str] | None,
) -> tuple[list[AppMetadataRow], list[StoredEngineReportRow], list[AppData], list[EngineReportRow]]:
    from machineconfig.jobs.installer.checks.install_utils import load_app_metadata_report, load_engine_results_report

    app_rows = _filter_app_metadata_rows(to_app_metadata_list(load_app_metadata_report()), normalized_app_names)
    engine_rows = _filter_stored_engine_rows(to_engine_report_rows(load_engine_results_report()), normalized_app_names)
    app_data_list = build_app_data_list(app_rows, engine_rows)
    hydrated_engine_rows = hydrate_engine_report_rows(app_rows, engine_rows)
    return app_rows, engine_rows, app_data_list, hydrated_engine_rows


def build_report_stats_lines(app_data_list: Sequence[AppData], app_metadata_path: Path, engine_results_path: Path) -> list[str]:
    scanned: list[AppData] = []
    clean: list[AppData] = []
    review: list[AppData] = []
    flagged: list[AppData] = []
    no_verdict: list[AppData] = []
    for row in app_data_list:
        positive_pct = row["positive_pct"]
        if positive_pct is None:
            continue
        scanned.append(row)
        if row["verdict_engines"] == 0:
            no_verdict.append(row)
            continue
        if positive_pct == 0.0:
            clean.append(row)
        elif positive_pct < 5.0:
            review.append(row)
        else:
            flagged.append(row)
    total_engines = sum(row.get("total_engines", 0) for row in app_data_list)
    verdict_engines = sum(row.get("verdict_engines", 0) for row in app_data_list)
    flagged_engines = sum(row.get("flagged_engines", 0) for row in app_data_list)
    return [
        f"Apps in report: {len(app_data_list)}",
        f"Scanned: {len(scanned)}",
        f"Clean: {len(clean)}",
        f"Review (<5%): {len(review)}",
        f"Flagged (>=5%): {len(flagged)}",
        f"No verdicts: {len(no_verdict)}",
        f"Engines: {total_engines}",
        f"Verdict engines: {verdict_engines}",
        f"Flagged engines: {flagged_engines}",
        f"App metadata CSV: {app_metadata_path}",
        f"Engine CSV: {engine_results_path}",
    ]


def build_report_options_text() -> str:
    from machineconfig.jobs.installer.checks.report_utils import APP_METADATA_KEYS, ENGINE_REPORT_KEYS

    return "\n".join(
        [
            "Views:",
            "  engines: full engine results table or raw engine CSV (default)",
            "  app-summary: compact derived app safety summary table",
            "  apps: app metadata CSV rows",
            "  stats: summary statistics for the selected apps",
            "  options: available views, formats, and CSV columns",
            "Formats:",
            "  table: rich table output for apps or engines",
            "  csv: raw CSV output for apps or engines",
            "Filter:",
            "  APPS accepts comma-separated app names",
            f"App CSV columns: {', '.join(APP_METADATA_KEYS)}",
            f"Engine CSV columns: {', '.join(ENGINE_REPORT_KEYS)}",
        ]
    )



def scan_single_path(path: Path, record: bool) -> None:
    from machineconfig.jobs.installer.checks.check_installations import build_scan_record, write_reports
    from machineconfig.jobs.installer.checks.vt_utils import get_vt_client, scan_file

    from rich.console import Console
    import typer
    from datetime import datetime
    console = Console()
    try:
        with get_vt_client() as client:
            scan_summary, scan_results = scan_file(path, client)

    except FileNotFoundError as e:
        console.print(f"[bold red]{e}[/bold red]")
        raise typer.Exit(code=1) from e
    if scan_summary is None:
        raise typer.Exit(code=1)

    console.print(
        f"{path.name}: {scan_summary['flagged_engines']}/{scan_summary['verdict_engines']} flagged "
        f"({scan_summary['positive_pct']:.1f}%) | "
        f"M:{scan_summary['malicious_engines']} S:{scan_summary['suspicious_engines']} "
        f"H:{scan_summary['harmless_engines']} U:{scan_summary['undetected_engines']}"
    )
    notes = str(scan_summary["notes"])
    if notes:
        console.print(f"Notes: {notes}")
    if not record:
        console.print("[yellow]Scan results were not saved to the repo reports.[/yellow]")
        return

    scan_record = build_scan_record(
        app_path=path,
        version=None,
        scan_time=datetime.now().strftime("%Y-%m-%d %H:%M"),
        app_url="",
        scan_summary=scan_summary,
        scan_results=scan_results,
        fallback_notes="VirusTotal scan failed or returned no summary.",
    )
    app_metadata_csv_path, engine_csv_path = write_reports([scan_record])
    console.print(f"[green]App metadata CSV report saved to: {app_metadata_csv_path}[/green]")
    console.print(f"[green]Engine CSV report saved to: {engine_csv_path}[/green]")
