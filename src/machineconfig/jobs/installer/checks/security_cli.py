from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer
import machineconfig.utils.path_core as path_core
from machineconfig.jobs.installer.checks.security_helper import (
    ReportFormat,
    ReportView,
    build_raw_csv_table,
    build_report_options_text,
    build_report_stats_lines,
    load_filtered_report_rows,
    normalize_app_names,
    parse_apps_argument,
    render_csv_text,
)

if TYPE_CHECKING:
    from rich.console import Console
    from rich.table import Table

    from machineconfig.utils.path_extended import PathExtended


@cache
def _console() -> Console:
    from rich.console import Console

    return Console()


def _resolve_report_view(view: ReportView | None, summarize: bool) -> ReportView:
    if view is not None:
        return view
    return "app-summary" if summarize else "engines"


def scan(
    apps: Annotated[str | None, typer.Argument(help="Optional comma-separated app names to scan")] = None,
    path: Annotated[
        Path | None,
        typer.Option(
            "--path", help="Optional file path to scan instead of installed apps", exists=True, file_okay=True, dir_okay=False, resolve_path=True
        ),
    ] = None,
    record: Annotated[
        bool | None,
        typer.Option(
            "--record/--no-record",
            help="Write scan results to the saved repo reports. Defaults to enabled for installed-app scans and disabled for --path scans.",
        ),
    ] = None,
) -> None:
    def run_scan(apps: str | None, path: Path | None, record: bool | None) -> None:
        from machineconfig.jobs.installer.checks.security_helper import parse_apps_argument, scan_single_path

        if apps is not None and path is not None:
            raise typer.BadParameter("Use either APPS or --path, not both.")
        resolved_record = record if record is not None else path is None
        if path is not None:
            scan_single_path(path, resolved_record)
        else:
            from machineconfig.jobs.installer.checks.check_installations import scan_installed_apps

            app_names = parse_apps_argument(apps)
            scan_installed_apps(app_names, write_reports_to_repo=resolved_record)

    from machineconfig.utils.code import run_lambda_function

    run_lambda_function(lambda: run_scan(apps=apps, path=path, record=record), uv_with=["vt-py"], uv_project_dir=None)


def _build_apps_table(apps_to_scan: list[tuple[PathExtended, str | None]]) -> Table:
    from rich.table import Table

    table = Table(title="Installed CLI Apps", show_lines=False)
    table.add_column("Name")
    table.add_column("Version", justify="right")
    table.add_column("Path")
    for app_path, version in apps_to_scan:
        table.add_row(app_path.stem, version or "", path_core.collapseuser(app_path, strict=False).as_posix())
    return table


def list_apps(apps: Annotated[str | None, typer.Argument(help="Optional comma-separated app names to list")] = None) -> None:
    from machineconfig.jobs.installer.checks.check_installations import collect_apps_to_scan

    apps_names = parse_apps_argument(apps)
    apps_to_scan = collect_apps_to_scan(apps_names)
    _console().print(_build_apps_table(apps_to_scan))


def upload(path: Annotated[Path, typer.Argument(..., help="Path to a local file to upload")]) -> None:
    from machineconfig.jobs.installer.checks.install_utils import upload_app
    from machineconfig.utils.path_extended import PathExtended

    link = upload_app(PathExtended(path))
    if not link:
        raise typer.Exit(code=1)
    _console().print(link)


def download(url: Annotated[str, typer.Argument(..., help="Google Drive URL or file id")]) -> None:
    from machineconfig.jobs.installer.checks.install_utils import download_google_drive_file

    path = download_google_drive_file(url)
    _console().print(path.as_posix())


def install(name: Annotated[str, typer.Argument(..., help="App name from app metadata report or 'essentials'")]) -> None:
    from machineconfig.jobs.installer.checks.install_utils import download_safe_apps

    download_safe_apps(name)


def summary() -> None:
    report(view="stats")


def report(
    apps: Annotated[str | None, typer.Argument(help="Optional comma-separated app names to show")] = None,
    view: Annotated[
        ReportView | None, typer.Option("--view", "-v", help="Which report view to show", case_sensitive=False, show_choices=True)
    ] = None,
    format_type: Annotated[
        ReportFormat, typer.Option("--format", "-f", help="Output format for apps or engines views", case_sensitive=False, show_choices=True)
    ] = "table",
    summarize: Annotated[bool, typer.Option("--summarize/--full", hidden=True)] = False,
) -> None:
    from machineconfig.jobs.installer.checks.install_utils import APP_METADATA_PATH, ENGINE_RESULTS_PATH
    from machineconfig.jobs.installer.checks.report_utils import (
        APP_METADATA_KEYS,
        ENGINE_REPORT_KEYS,
        build_engine_results_table,
        build_summary_group,
    )

    resolved_view = _resolve_report_view(view, summarize)
    if resolved_view == "options":
        _console().print(build_report_options_text())
        return
    if resolved_view not in {"apps", "engines"} and format_type != "table":
        raise typer.BadParameter("--format csv is only supported with --view apps or --view engines.")

    apps_names = parse_apps_argument(apps)
    normalized_app_names = normalize_app_names(apps_names)
    app_rows, engine_rows, app_data_list, hydrated_engine_rows = load_filtered_report_rows(normalized_app_names)

    if resolved_view == "stats":
        if not app_data_list:
            raise typer.Exit(code=1)
        for line in build_report_stats_lines(app_data_list, APP_METADATA_PATH, ENGINE_RESULTS_PATH):
            _console().print(line)
        return
    if resolved_view == "app-summary":
        if not app_data_list:
            raise typer.Exit(code=1)
        _console().print(build_summary_group(app_data_list))
        return
    if resolved_view == "apps":
        if not app_rows:
            raise typer.Exit(code=1)
        if format_type == "csv":
            _console().print(render_csv_text(app_rows, APP_METADATA_KEYS))
            return
        _console().print(build_raw_csv_table("App Metadata CSV", app_rows, APP_METADATA_KEYS))
        return
    if not engine_rows:
        raise typer.Exit(code=1)
    if format_type == "csv":
        _console().print(render_csv_text(engine_rows, ENGINE_REPORT_KEYS))
        return
    _console().print(build_engine_results_table(hydrated_engine_rows))


def get_app() -> typer.Typer:
    app = typer.Typer(name="security-cli", help="Security related CLI tools.", no_args_is_help=True, add_help_option=True, add_completion=False)

    app.command(name="scan", help="<s> Scan installed apps or a single file path with VirusTotal", no_args_is_help=True)(scan)
    app.command(name="s", help="<s> Scan installed apps or a single file path with VirusTotal", hidden=True, no_args_is_help=True)(scan)
    app.command(name="list", help="<l> List installed apps, optionally filtered by comma-separated app names", no_args_is_help=True)(list_apps)
    app.command(name="l", help="<l> List installed apps, optionally filtered by comma-separated app names", hidden=True, no_args_is_help=True)(list_apps)
    app.command(name="upload", help="<u> Upload a local file to cloud storage", no_args_is_help=True)(upload)
    app.command(name="u", help="<u> Upload a local file to cloud storage", hidden=True, no_args_is_help=True)(upload)
    app.command(name="download", help="<d> Download a file from Google Drive", no_args_is_help=True)(download)
    app.command(name="d", help="<d> Download a file from Google Drive", hidden=True, no_args_is_help=True)(download)
    app.command(name="install", help="<i> Install safe apps from app metadata report", no_args_is_help=True)(install)
    app.command(name="i", help="<i> Install safe apps from app metadata report", hidden=True, no_args_is_help=True)(install)
    app.command(name="report", help="<r> Show the full saved scan report by default, or CSV rows/summary stats")(report)
    app.command(name="r", help="<r> Show the full saved scan report by default, or CSV rows/summary stats", hidden=True)(report)

    return app
