"""
Check Installations
===================

This module scans installed applications using VirusTotal and generates a safety report.
It also provides functionality to download and install pre-checked applications.
"""

import csv
from datetime import datetime
from pathlib import Path
from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

from machineconfig.jobs.installer.checks.install_utils import APP_METADATA_PATH, ENGINE_RESULTS_PATH, upload_app
from machineconfig.jobs.installer.checks.report_utils import (
    APP_METADATA_KEYS,
    ENGINE_REPORT_KEYS,
    AppData,
    ScannedAppRecord,
    build_app_metadata_row,
    build_engine_report_rows,
    build_latest_scan_panel,
    build_summary_group,
)
from machineconfig.jobs.installer.checks.vt_utils import ScanResult, ScanSummary, get_vt_client, scan_file
from machineconfig.utils.installer_utils.installer_runner import get_installed_cli_apps
from machineconfig.utils.path_extended import PathExtended
from machineconfig.utils.source_of_truth import INSTALL_VERSION_ROOT

console = Console()


def _normalize_app_names(app_names: list[str]) -> list[str]:
    return [name.strip().lower() for name in app_names if name.strip()]


def _build_version_lookup() -> dict[str, str]:
    install_version_root_ext = PathExtended(INSTALL_VERSION_ROOT)
    version_files = list(install_version_root_ext.search()) if install_version_root_ext.exists() else []
    versions: dict[str, str] = {}
    for version_file in version_files:
        versions[version_file.stem] = version_file.read_text(encoding="utf-8").strip()
    return versions


def collect_apps_to_scan(app_names: list[str] | None) -> list[tuple[PathExtended, str | None]]:
    with console.status("[bold green]Gathering installed applications...[/bold green]"):
        apps_paths = get_installed_cli_apps()
        if app_names is not None:
            normalized = set(_normalize_app_names(app_names))
            apps_paths = [app_path for app_path in apps_paths if app_path.stem.lower() in normalized]
        versions = _build_version_lookup()
        apps_to_scan: list[tuple[PathExtended, str | None]] = []
        for app_path in apps_paths:
            version = versions.get(app_path.stem)
            apps_to_scan.append((app_path, version))
    return apps_to_scan


def _build_scan_progress_renderable(progress: Progress, last_scanned: AppData | None, completed_count: int, total_count: int) -> RenderableType:
    return Group(progress, build_latest_scan_panel(last_scanned, completed_count, total_count))


def _build_app_data(
    app_path: PathExtended,
    version: str | None,
    scan_time: str,
    app_url: str,
    scan_summary: ScanSummary | None,
    fallback_notes: str,
) -> AppData:
    app_data: AppData = {
        "app_name": app_path.stem,
        "version": version,
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
        "notes": fallback_notes,
        "scan_time": scan_time,
        "app_path": app_path.collapseuser(strict=False).as_posix(),
        "app_url": app_url,
    }
    if scan_summary is not None:
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
    return app_data


def build_scan_record(
    app_path: PathExtended,
    version: str | None,
    scan_time: str,
    app_url: str,
    scan_summary: ScanSummary | None,
    scan_results: list[ScanResult],
    fallback_notes: str,
) -> ScannedAppRecord:
    app_data = _build_app_data(
        app_path=app_path,
        version=version,
        scan_time=scan_time,
        app_url=app_url,
        scan_summary=scan_summary,
        fallback_notes=fallback_notes,
    )
    return {"app_data": app_data, "engine_results": build_engine_report_rows(app_data, scan_results)}


def _extract_app_data(scan_records: list[ScannedAppRecord]) -> list[AppData]:
    return [scan_record["app_data"] for scan_record in scan_records]


def scan_apps_with_vt(apps_to_scan: list[tuple[PathExtended, str | None]]) -> list[ScannedAppRecord]:
    scan_records: list[ScannedAppRecord] = []
    if not apps_to_scan:
        return scan_records
    try:
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
        )
        scan_task = progress.add_task("[cyan]Scanning apps...", total=len(apps_to_scan))
        last_scanned: AppData | None = None
        with Live(_build_scan_progress_renderable(progress, last_scanned, 0, len(apps_to_scan)), console=console, refresh_per_second=8) as live:
            progress.start()
            try:
                with get_vt_client() as client:
                    for app_path, version in apps_to_scan:
                        progress.update(scan_task, description=f"Scanning {app_path.name}...")
                        live.update(_build_scan_progress_renderable(progress, last_scanned, len(scan_records), len(apps_to_scan)))
                        scan_summary, scan_results = scan_file(app_path, client, progress, scan_task)
                        progress.update(scan_task, description=f"Uploading {app_path.name}...")
                        live.update(_build_scan_progress_renderable(progress, last_scanned, len(scan_records), len(apps_to_scan)))
                        app_url = upload_app(app_path) or ""
                        scan_time = datetime.now().strftime("%Y-%m-%d %H:%M")
                        scan_record = build_scan_record(
                            app_path=app_path,
                            version=version,
                            scan_time=scan_time,
                            app_url=app_url,
                            scan_summary=scan_summary,
                            scan_results=scan_results,
                            fallback_notes="VirusTotal scan failed or returned no summary.",
                        )
                        last_scanned = scan_record["app_data"]
                        scan_records.append(scan_record)
                        progress.advance(scan_task)
                        live.update(_build_scan_progress_renderable(progress, last_scanned, len(scan_records), len(apps_to_scan)))
            finally:
                progress.stop()
    except FileNotFoundError as e:
        console.print(f"[bold red]{e}[/bold red]")
        console.print("[yellow]Skipping scanning due to missing credentials.[/yellow]")
        for app_path, version in apps_to_scan:
            scan_records.append(
                build_scan_record(
                    app_path=app_path,
                    version=version,
                    scan_time=datetime.now().strftime("%Y-%m-%d %H:%M"),
                    app_url="",
                    scan_summary=None,
                    scan_results=[],
                    fallback_notes="VirusTotal credentials missing.",
                )
            )
    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred during scanning: {e}[/bold red]")
    return scan_records


def write_reports(scan_records: list[ScannedAppRecord]) -> tuple[Path, Path]:
    app_data_list = _extract_app_data(scan_records)
    if not app_data_list:
        raise ValueError("No app data available to write reports.")
    APP_METADATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(APP_METADATA_PATH, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=list(APP_METADATA_KEYS))
        writer.writeheader()
        writer.writerows([build_app_metadata_row(scan_record["app_data"]) for scan_record in scan_records])
    engine_results = [engine_row for scan_record in scan_records for engine_row in scan_record["engine_results"]]
    with open(ENGINE_RESULTS_PATH, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=list(ENGINE_REPORT_KEYS))
        writer.writeheader()
        writer.writerows(engine_results)
    return APP_METADATA_PATH, ENGINE_RESULTS_PATH


def scan_installed_apps(app_names: list[str] | None, write_reports_to_repo: bool) -> list[AppData]:
    console.rule("[bold blue]MachineConfig Installation Checker[/bold blue]")
    apps_to_scan = collect_apps_to_scan(app_names)
    console.print(f"[green]Found {len(apps_to_scan)} applications to check.[/green]")
    scan_records = scan_apps_with_vt(apps_to_scan)
    app_data_list = _extract_app_data(scan_records)
    if app_data_list:
        console.print(build_summary_group(app_data_list))
        if write_reports_to_repo:
            app_metadata_csv_path, engine_csv_path = write_reports(scan_records)
            console.print(f"[green]App metadata CSV report saved to: {app_metadata_csv_path}[/green]")
            console.print(f"[green]Engine CSV report saved to: {engine_csv_path}[/green]")
        else:
            console.print("[yellow]Scan results were not saved to the repo reports.[/yellow]")
    return app_data_list


def scan_and_write_reports(app_names: list[str] | None) -> list[AppData]:
    return scan_installed_apps(app_names, write_reports_to_repo=True)


def main() -> None:
    scan_and_write_reports(None)


if __name__ == "__main__":
    main()
