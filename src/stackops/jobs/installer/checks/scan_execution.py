from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock

import typer
from rich.console import Console, Group
from rich.live import Live
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

from stackops.jobs.installer.checks.app_upload import upload_app
from stackops.jobs.installer.checks.report_utils import AppData, ScannedAppRecord, build_latest_scan_panel, build_summary_group
from stackops.jobs.installer.checks.scan_history import RunScope, RunStatus, create_run, save_run
from stackops.jobs.installer.checks.scan_outcomes import ScanSuccess
from stackops.jobs.installer.checks.scan_records import build_scan_record
from stackops.jobs.installer.checks.vt_account_report import build_account_report, render_account_csv
from stackops.jobs.installer.checks.vt_account_stats import VirusTotalAccountStats
from stackops.jobs.installer.checks.vt_display import build_vt_parallelism_panel
from stackops.jobs.installer.checks.vt_workers import ScannedFile, scan_files_with_vt
from stackops.secrets.readers import read_virus_total_api_keys

console = Console()


def execute_scan(
    apps_to_scan: list[tuple[Path, str | None]],
    scope: RunScope,
    requested: list[str],
    record: bool,
    upload: bool,
    concurrency: int | None,
    records_root: Path,
) -> list[AppData]:
    run = create_run(records_root, scope, requested, apps_to_scan, concurrency) if record else None
    stats = VirusTotalAccountStats(())
    records_by_index: dict[int, ScannedAppRecord] = {}
    record_lock = Lock()
    accepting_results = True
    status: RunStatus = "running"
    message: str | None = None
    operation = "Scan setup"

    def record_result(scanned_file: ScannedFile) -> None:
        scan_record = build_scan_record(scanned_file.path, scanned_file.version, "", scanned_file.outcome)
        checked_at = datetime.now(UTC).isoformat()
        with record_lock:
            if not accepting_results:
                return
            records_by_index[scanned_file.index] = scan_record
            if run is not None:
                target = run["targets"][scanned_file.index]
                target["checked_at"] = checked_at
                target["sha256"] = scanned_file.outcome.sha256
                target["record"] = scan_record
                if isinstance(scanned_file.outcome, ScanSuccess):
                    target["source"] = scanned_file.outcome.source
                else:
                    target["error"] = {
                        "stage": scanned_file.outcome.stage,
                        "error_type": scanned_file.outcome.error_type,
                        "error_code": scanned_file.outcome.error_code,
                    }
                run["account_csv"] = render_account_csv(stats)
                save_run(records_root, run)

    try:
        if run is not None:
            console.print(f"""[cyan]Recording scan run: {run['run_id']}[/cyan]""")
        else:
            console.print("[yellow]Recording disabled for this scan.[/yellow]")
        console.print("[cyan]Cloud uploads enabled.[/cyan]" if upload else "[dim]Cloud uploads disabled; use --upload (-u) to enable.[/dim]")
        if not apps_to_scan:
            status = "empty"
            message = "No applications matched the requested scan."
            console.print(f"""[yellow]{message}[/yellow]""")
        else:
            operation = "VirusTotal credential loading"
            credentials = read_virus_total_api_keys()
            stats = VirusTotalAccountStats(tuple(credential.account_name for credential in credentials))
            worker_count = min(len(credentials) if concurrency is None else concurrency, len(apps_to_scan))
            console.print(build_vt_parallelism_panel(account_count=len(credentials), concurrency=worker_count))
            progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=console,
            )
            scan_task = progress.add_task(f"""[cyan]Processing with {worker_count} VirusTotal workers...""", total=len(apps_to_scan))
            operation = "VirusTotal scanning"
            with (
                Live(Group(progress, build_latest_scan_panel(None, 0, len(apps_to_scan))), console=console, refresh_per_second=8) as live,
                closing(scan_files_with_vt(apps_to_scan, credentials, concurrency, stats, record_result)) as scanned_files,
            ):
                for completed_count, scanned_file in enumerate(scanned_files, start=1):
                    with record_lock:
                        scan_record = records_by_index[scanned_file.index]
                    if upload and isinstance(scanned_file.outcome, ScanSuccess):
                        progress.update(scan_task, description=f"""Uploading {scanned_file.path.name}...""")
                        operation = "Cloud upload"
                        app_url = upload_app(path=scanned_file.path, expected_sha256=scanned_file.outcome.sha256)
                        with record_lock:
                            scan_record["app_data"]["app_url"] = app_url
                            if run is not None:
                                run["account_csv"] = render_account_csv(stats)
                                save_run(records_root, run)
                        operation = "VirusTotal scanning"
                    progress.advance(scan_task)
                    progress.update(scan_task, description=f"""[cyan]Processing with {worker_count} VirusTotal workers...""")
                    live.update(Group(progress, build_latest_scan_panel(scan_record["app_data"], completed_count, len(apps_to_scan))))
            app_data_list = [records_by_index[index]["app_data"] for index in sorted(records_by_index)]
            console.print(build_summary_group(app_data_list))
            failed_count = sum(app_data["positive_pct"] is None for app_data in app_data_list)
            status = "completed_with_errors" if failed_count else "completed"
            if failed_count:
                message = f"""{failed_count} of {len(apps_to_scan)} VirusTotal scans failed."""
                console.print(f"""[bold red]{message} See the scan notes for errors.[/bold red]""")
    except KeyboardInterrupt:
        status = "interrupted"
        message = "Scan interrupted."
        raise
    except BaseException as exc:
        status = "failed"
        message = f"""{operation} failed ({type(exc).__name__})."""
        raise
    finally:
        with record_lock:
            accepting_results = False
            if run is not None:
                run["status"] = status
                run["finished_at"] = datetime.now(UTC).isoformat()
                run["message"] = message
                run["account_csv"] = render_account_csv(stats)
                save_run(records_root, run)
        console.print(build_account_report(stats))
        if run is not None:
            console.print(f"""[green]Scan run saved: {run['run_id']} ({status})[/green]""")
    if status in {"empty", "completed_with_errors"}:
        raise typer.Exit(code=1)
    return [records_by_index[index]["app_data"] for index in sorted(records_by_index)]
