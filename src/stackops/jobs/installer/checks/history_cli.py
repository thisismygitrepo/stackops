from pathlib import Path
from typing import Annotated, Literal

import typer
from rich.console import Console

from stackops.jobs.installer.checks.constants import SECURITY_RECORDS_ROOT
from stackops.jobs.installer.checks.report_utils import build_summary_group
from stackops.jobs.installer.checks.run_reports import APP_EXPORT_KEYS, APP_TABLE_KEYS, ENGINE_EXPORT_KEYS, build_run_rows, export_run
from stackops.jobs.installer.checks.scan_history import ScanRun, list_runs, load_run
from stackops.jobs.installer.checks.security_helper import build_raw_csv_table, parse_apps_argument, render_csv_text

console = Console()
ReportView = Literal["engines", "app-summary", "apps", "options", "stats", "accounts"]
ReportFormat = Literal["table", "csv"]


def selected_run(records_dir: Path, run_id: str | None) -> ScanRun:
    try:
        return load_run(records_dir.expanduser().absolute(), run_id)
    except (FileNotFoundError, ValueError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc


def history(
    apps: Annotated[str | None, typer.Argument(help="Only runs targeting these comma-separated app names")] = None,
    limit: Annotated[int, typer.Option("--limit", min=1, help="Maximum runs to show, newest first")] = 20,
    format_type: Annotated[ReportFormat, typer.Option("--format", "-f", help="Table or raw CSV")] = "table",
    records_dir: Annotated[Path, typer.Option("--records-dir", help="Scan history directory")] = SECURITY_RECORDS_ROOT,
) -> None:
    records_dir = records_dir.expanduser().absolute()
    try:
        app_names = parse_apps_argument(apps)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    names = {name.lower() for name in app_names} if app_names is not None else None
    rows: list[dict[str, object]] = []
    for run in list_runs(records_dir):
        run_names = {Path(target["path"]).stem.lower() for target in run["targets"]}
        if run["scope"] == "apps":
            run_names.update(name.lower() for name in run["requested"])
        if names is not None and not names.intersection(run_names):
            continue
        completed = sum(target["record"] is not None for target in run["targets"])
        failed = sum(target["error"] is not None for target in run["targets"])
        rows.append({
            "run_id": run["run_id"], "started_at": run["started_at"], "scope": run["scope"],
            "requested": ", ".join(run["requested"]) or "all installed apps",
            "status": "unfinished" if run["status"] == "running" else run["status"],
            "results": f"""{completed}/{len(run['targets'])}""", "failed": failed,
        })
        if len(rows) == limit:
            break
    columns = ("run_id", "started_at", "scope", "requested", "status", "results", "failed")
    if format_type == "csv":
        typer.echo(render_csv_text(rows, columns))
        return
    if not rows:
        typer.echo(f"""No matching scan runs in {records_dir}.""")
        return
    console.print(build_raw_csv_table("Scan History", rows, columns))
    typer.echo("Unfinished means no final status was recorded; the scan may still be running or may have stopped abruptly.")


def report(
    apps: Annotated[str | None, typer.Argument(help="Filter targets within the selected run by comma-separated app names")] = None,
    run: Annotated[str | None, typer.Option("--run", help="Exact run ID; defaults to the latest started run")] = None,
    view: Annotated[ReportView, typer.Option("--view", "-v", help="Report view")] = "engines",
    format_type: Annotated[ReportFormat, typer.Option("--format", "-f", help="Table or raw CSV")] = "table",
    records_dir: Annotated[Path, typer.Option("--records-dir", help="Scan history directory")] = SECURITY_RECORDS_ROOT,
) -> None:
    records_dir = records_dir.expanduser().absolute()
    if view == "options":
        typer.echo("Views: engines (default), apps, app-summary, stats, accounts, options.\n"
                   "--run ID selects one run; otherwise the latest started run is used, including unfinished runs.\n"
                   "APPS filters only that run; use history APPS to find older matching runs.\n"
                   "--format csv supports apps, engines, and accounts. Export saves a complete run to a new directory.\n"
                   "checked_at is this run's UTC observation time; analyzed_at is the original VirusTotal analysis time.\n"
                   "source distinguishes existing_report from submitted_file. Unscanned targets stay visible.")
        return
    if format_type == "csv" and view not in {"apps", "engines", "accounts"}:
        raise typer.BadParameter("CSV is supported for apps, engines, and accounts.")
    if view == "accounts" and apps is not None:
        raise typer.BadParameter("Account statistics cover the whole run; omit APPS.")
    try:
        app_names = parse_apps_argument(apps)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    names = {name.lower() for name in app_names} if app_names is not None else None
    saved = selected_run(records_dir, run)
    app_rows, engine_rows = build_run_rows(saved, names)
    if names is not None and not app_rows:
        typer.echo(f"""No matching targets in run {saved['run_id']}. Use history to find another run.""", err=True)
        raise typer.Exit(code=1)
    if format_type == "csv":
        if view == "accounts":
            typer.echo(saved["account_csv"], nl=False)
        else:
            rows, columns = (app_rows, APP_EXPORT_KEYS) if view == "apps" else (engine_rows, ENGINE_EXPORT_KEYS)
            typer.echo(render_csv_text(rows, columns))
        return
    status = "unfinished (running or stopped without finalization)" if saved["status"] == "running" else saved["status"]
    typer.echo("\n".join((
        f"""Run: {saved['run_id']}""",
        f"""Scope: {saved['scope']} ({', '.join(saved['requested']) or 'all installed apps'})""",
        f"""Started: {saved['started_at']}""", f"""Finished: {saved['finished_at'] or '-'}""",
        f"""Status: {status}""", f"""Record: {records_dir / saved['run_id'] / 'run.json'}""",
    )))
    if saved["message"]:
        typer.echo(saved["message"])
    if view == "accounts":
        import csv
        from io import StringIO

        account_rows = list(csv.DictReader(StringIO(saved["account_csv"])))
        if account_rows:
            console.print(build_raw_csv_table("Account Statistics", account_rows, tuple(account_rows[0])))
        else:
            typer.echo("No account statistics recorded.")
        return
    data = [target["record"]["app_data"] for target in saved["targets"]
            if target["record"] is not None and (names is None or target["record"]["app_data"]["app_name"].lower() in names)]
    if view == "stats":
        typer.echo("\n".join((
            f"""Selected targets: {len(app_rows)}""", f"""Recorded results: {len(data)}""",
            f"""Failed: {sum(row['status'] == 'failed' for row in app_rows)}""",
            f"""Without a result: {len(app_rows) - len(data)}""", f"""Engine results: {len(engine_rows)}""",
        )))
        if data:
            console.print(build_summary_group(data))
        return
    console.print(build_raw_csv_table("Run Targets (timestamps in UTC)", app_rows, APP_TABLE_KEYS))
    if view == "app-summary" and data:
        console.print(build_summary_group(data))
    elif view == "engines":
        if engine_rows:
            console.print(build_raw_csv_table("Engine Results", engine_rows, ("target_id", "app_name", "engine_name", "engine_category", "engine_result")))
        else:
            typer.echo("No engine results recorded in this selection.")


def export(
    output: Annotated[Path, typer.Option("--output", "-o", help="New directory for run.json, apps.csv, engines.csv, and accounts.csv")],
    run: Annotated[str | None, typer.Option("--run", help="Exact run ID; defaults to the latest started run")] = None,
    records_dir: Annotated[Path, typer.Option("--records-dir", help="Scan history directory")] = SECURITY_RECORDS_ROOT,
) -> None:
    saved = selected_run(records_dir, run)
    output = output.expanduser().absolute()
    try:
        export_run(saved, output)
    except FileExistsError as exc:
        raise typer.BadParameter("Output directory already exists; choose a new directory.", param_hint="--output") from exc
    typer.echo(f"""Exported run {saved['run_id']} to {output.absolute()}""")
