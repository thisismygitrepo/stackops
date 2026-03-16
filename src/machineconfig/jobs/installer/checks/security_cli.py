

from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer

if TYPE_CHECKING:
    from rich.console import Console
    from rich.table import Table

    from machineconfig.jobs.installer.checks.report_utils import AppData
    from machineconfig.utils.path_extended import PathExtended


@cache
def _console() -> Console:
    from rich.console import Console
    return Console()


# def _parse_apps_csv(apps_csv: str | None) -> list[str] | None:
#     if apps_csv is None:
#         return None
#     app_names = [name.strip() for name in apps_csv.split(",") if name.strip()]
#     return app_names or None


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


def _to_app_data_list(rows: list[dict[str, object]]) -> list[AppData]:
    app_data_list: list[AppData] = []
    for row in rows:
        app_name = str(row.get("app_name", ""))
        version_raw = row.get("version")
        version = str(version_raw) if version_raw not in {None, ""} else None
        positive_pct = _parse_positive_pct(str(row.get("positive_pct", "")))
        scan_time = str(row.get("scan_time", ""))
        app_path = str(row.get("app_path", ""))
        app_url = str(row.get("app_url", ""))
        app_data_list.append(
            {
                "app_name": app_name,
                "version": version,
                "positive_pct": positive_pct,
                "scan_time": scan_time,
                "app_path": app_path,
                "app_url": app_url,
            }
        )
    return app_data_list


def scan_apps(
    apps: Annotated[str | None, typer.Argument(help="Optional comma-separated app names to scan")] = None,
) -> None:
    def func(apps__: str | None) -> None:
        from machineconfig.jobs.installer.checks.check_installations import scan_and_write_reports
        # app_names = _parse_apps_csv(apps__)
        app_names = [name.strip() for name in apps__.split(",")] if apps__ else None
        scan_and_write_reports(app_names)
    from machineconfig.utils.code import run_lambda_function
    run_lambda_function(lambda: func(apps__=apps), uv_with=["vt-py"], uv_project_dir=None)


def _build_apps_table(apps_to_scan: list[tuple[PathExtended, str | None]]) -> Table:
    from rich.table import Table
    table = Table(title="Installed CLI Apps", show_lines=False)
    table.add_column("Name")
    table.add_column("Version", justify="right")
    table.add_column("Path")
    for app_path, version in apps_to_scan:
        table.add_row(app_path.stem, version or "", app_path.collapseuser(strict=False).as_posix())
    return table


def list_apps(
    apps: Annotated[str | None, typer.Argument(help="Optional comma-separated app names to list")] = None,
) -> None:
    from machineconfig.jobs.installer.checks.check_installations import collect_apps_to_scan

    # app_names = _parse_apps_csv(apps)
    app_names = [name.strip() for name in apps.split(",")] if apps else None
    apps_to_scan = collect_apps_to_scan(app_names)
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


def install(name: Annotated[str, typer.Argument(..., help="App name from summary report or 'essentials'")]) -> None:
    from machineconfig.jobs.installer.checks.install_utils import download_safe_apps

    download_safe_apps(name)


def summary() -> None:
    from machineconfig.jobs.installer.checks.check_installations import APP_SUMMARY_PATH
    from machineconfig.jobs.installer.checks.install_utils import load_summary_report

    rows = load_summary_report()
    if not rows:
        raise typer.Exit(code=1)
    app_data_list = _to_app_data_list(rows)
    scanned = [row for row in app_data_list if row.get("positive_pct") is not None]
    clean = [row for row in scanned if row.get("positive_pct") == 0.0]
    _console().print(f"Apps in report: {len(app_data_list)}")
    _console().print(f"Scanned: {len(scanned)}")
    _console().print(f"Clean (0%): {len(clean)}")
    _console().print(f"Report CSV: {APP_SUMMARY_PATH.with_suffix('.csv')}")
    _console().print(f"Report MD: {APP_SUMMARY_PATH.with_suffix('.md')}")


def report() -> None:
    from machineconfig.jobs.installer.checks.check_installations import APP_SUMMARY_PATH
    from machineconfig.jobs.installer.checks.install_utils import load_summary_report
    from machineconfig.jobs.installer.checks.report_utils import generate_markdown_report

    rows = load_summary_report()
    if not rows:
        raise typer.Exit(code=1)
    app_data_list = _to_app_data_list(rows)
    md_path = APP_SUMMARY_PATH.with_suffix(".md")
    generate_markdown_report(app_data_list, md_path)
    _console().print(f"Markdown report saved to: {md_path}")


def scan_path(path: Annotated[Path, typer.Argument(..., help="Path to a file to scan")]) -> None:
    from machineconfig.jobs.installer.checks.vt_utils import get_vt_client, scan_file
    from machineconfig.utils.path_extended import PathExtended

    try:
        client = get_vt_client()
    except FileNotFoundError as e:
        _console().print(f"[bold red]{e}[/bold red]")
        raise typer.Exit(code=1)
    positive_pct, _ = scan_file(PathExtended(path), client)
    _console().print(f"{path.name}: {positive_pct}% positives")


def get_app() -> typer.Typer:
    app = typer.Typer(
        name="security-cli",
        help="Security related CLI tools.",
        no_args_is_help=True,
        add_help_option=True,
        add_completion=False,
    )

    app.command(name="scan", help="Scan installed apps, optionally filtered by comma-separated app names")(scan_apps)
    app.command(name="list", help="List installed apps, optionally filtered by comma-separated app names")(list_apps)
    app.command(name="upload", help="Upload a local file to cloud storage")(upload)
    app.command(name="download", help="Download a file from Google Drive")(download)
    app.command(name="install", help="Install safe apps from summary report")(install)
    app.command(name="summary", help="Show summary statistics for the last report")(summary)
    app.command(name="report", help="Regenerate Markdown report from CSV summary")(report)
    app.command(name="scan-path", help="Scan a single file path with VirusTotal")(scan_path)

    return app
