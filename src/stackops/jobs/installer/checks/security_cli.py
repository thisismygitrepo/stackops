from pathlib import Path
from typing import Annotated

import typer

from stackops.jobs.installer.checks.constants import SCAN_HELP, SECURITY_RECORDS_ROOT
from stackops.jobs.installer.checks.history_cli import export, history, report, selected_run
from stackops.jobs.installer.checks.security_helper import parse_apps_argument


def _run_scan(app_names: list[str] | None, path_value: str | None, record: bool, concurrency: int | None, records_dir: str) -> None:
    from pathlib import Path

    import typer

    from stackops.jobs.installer.checks.scan_execution import execute_scan

    try:
        if path_value is not None:
            execute_scan([(Path(path_value), None)], scope="path", requested=[path_value], record=record,
                         concurrency=concurrency, records_root=Path(records_dir))
        else:
            from stackops.jobs.installer.checks.check_installations import collect_apps_to_scan

            execute_scan(collect_apps_to_scan(app_names), scope="all" if app_names is None else "apps",
                         requested=app_names or [], record=record, concurrency=concurrency, records_root=Path(records_dir))
    except typer.Exit as exc:
        raise SystemExit(exc.exit_code) from None


def scan(
    apps: Annotated[str | None, typer.Argument(help="Comma-separated installed app names")] = None,
    path: Annotated[Path | None, typer.Option("--path", "-p", help="Scan a single file", exists=True,
                                           file_okay=True, dir_okay=False, resolve_path=True)] = None,
    all_apps: Annotated[bool, typer.Option("--all", help="Scan all installed apps")] = False,
    record: Annotated[bool, typer.Option("--record/--no-record", help="Save this scan as a separate history run")] = True,
    concurrency: Annotated[int | None, typer.Option("--concurrency", min=1, help="Maximum concurrent files; defaults to account count")] = None,
    records_dir: Annotated[Path, typer.Option("--records-dir", help="Scan history directory")] = SECURITY_RECORDS_ROOT,
) -> None:
    if sum((apps is not None, path is not None, all_apps)) != 1:
        raise typer.BadParameter("Choose exactly one of APPS, --path FILE, or --all.")
    if concurrency is not None and concurrency < 1:
        raise typer.BadParameter("Must be at least 1.", param_hint="--concurrency")
    try:
        app_names = parse_apps_argument(apps)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    path_value = str(path) if path is not None else None
    records_value = str(records_dir.expanduser().absolute())

    from stackops.utils.code import run_lambda_function

    proc = run_lambda_function(
        lambda: _run_scan(app_names=app_names, path_value=path_value, record=record, concurrency=concurrency, records_dir=records_value),
        uv_with=["vt-py"], uv_project_dir=None,
    )
    if proc.returncode != 0:
        raise typer.Exit(code=proc.returncode)


def list_apps(apps: Annotated[str | None, typer.Argument(help="Optional comma-separated app names to list")] = None) -> None:
    from rich.console import Console
    from rich.table import Table

    from stackops.jobs.installer.checks.check_installations import collect_apps_to_scan

    try:
        app_names = parse_apps_argument(apps)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    apps_to_scan = collect_apps_to_scan(app_names)
    if not apps_to_scan:
        typer.echo("No matching installed CLI apps found.", err=True)
        raise typer.Exit(code=1)
    table = Table(title="Installed CLI Apps")
    for heading in ("Name", "Version", "Path"):
        table.add_column(heading)
    for app_path, version in apps_to_scan:
        table.add_row(app_path.stem, version or "", app_path.as_posix())
    Console().print(table)


def upload(path: Annotated[Path, typer.Argument(help="Path to a local file to upload")]) -> None:
    from stackops.jobs.installer.checks.install_utils import upload_app

    link = upload_app(path)
    if not link:
        raise typer.Exit(code=1)
    typer.echo(link)


def download(url: Annotated[str, typer.Argument(help="Google Drive URL or file id")]) -> None:
    from stackops.jobs.installer.checks.install_utils import download_google_drive_file

    path = download_google_drive_file(url)
    typer.echo(path.as_posix())


def install(
    name: Annotated[str, typer.Argument(help="App name from the selected run, or 'essentials'")],
    run: Annotated[str | None, typer.Option("--run", help="Exact run ID; defaults to the latest started run")] = None,
    records_dir: Annotated[Path, typer.Option("--records-dir", help="Scan history directory")] = SECURITY_RECORDS_ROOT,
) -> None:
    from stackops.jobs.installer.checks.install_utils import download_safe_apps

    saved = selected_run(records_dir, run)
    typer.echo(f"""Using scan run {saved['run_id']} ({saved['status']}).""")
    if not download_safe_apps(name, saved):
        raise typer.Exit(code=1)


def get_app() -> typer.Typer:
    app = typer.Typer(name="security-cli", help="Security scans with durable per-run history.", no_args_is_help=True,
                      add_help_option=True, add_completion=False, context_settings={"help_option_names": ["-h", "--help"]})
    app.command(name="scan", help=SCAN_HELP, no_args_is_help=True)(scan)
    app.command(name="s", help=SCAN_HELP, hidden=True, no_args_is_help=True)(scan)
    app.command(name="list", help="<l> List installed apps")(list_apps)
    app.command(name="l", hidden=True)(list_apps)
    app.command(name="upload", help="<u> Upload a local file", no_args_is_help=True)(upload)
    app.command(name="u", hidden=True, no_args_is_help=True)(upload)
    app.command(name="download", help="<d> Download a file from Google Drive", no_args_is_help=True)(download)
    app.command(name="d", hidden=True, no_args_is_help=True)(download)
    app.command(name="install", help="<i> Install safe apps from one saved run", no_args_is_help=True)(install)
    app.command(name="i", hidden=True, no_args_is_help=True)(install)
    app.command(name="report", help="<r> Inspect one run; defaults to the latest started run")(report)
    app.command(name="r", hidden=True)(report)
    app.command(name="history", help="List saved scan runs, newest first")(history)
    app.command(name="export", help="Export one run to a new directory", no_args_is_help=True)(export)
    return app
