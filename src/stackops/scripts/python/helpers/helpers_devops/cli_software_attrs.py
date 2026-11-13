from pathlib import Path
from typing import Annotated, Literal

import typer


def update_attrs(
    source: Annotated[
        Literal["library", "l", "user", "u"],
        typer.Option("--source", "-s", help="Catalog to update: library or user. Updates one YAML file at a time."),
    ] = "library",
    path: Annotated[Path | None, typer.Option("--custom-path", "-p", help="Use another user catalog with --source user.")] = None,
    report_path: Annotated[
        Path | None,
        typer.Option("--report-path", "-o", help="CSV output path; defaults to profile/records/github_commit_dates.csv in the config root."),
    ] = None,
) -> None:
    from rich.console import Console

    from stackops.utils.installer_utils.github_commit_dates_constants import COMMIT_DATE_REPORT_PATH
    from stackops.utils.installer_utils.installer_catalog import LIBRARY_INSTALLER_DATA_PATH, USER_INSTALLER_DATA_PATH, InstallerDataFileError
    from stackops.utils.installer_utils.update_github_commit_dates import update_installer_commit_dates

    if source in {"library", "l"}:
        if path is not None:
            raise typer.BadParameter("--custom-path requires --source user.")
        catalog_path = LIBRARY_INSTALLER_DATA_PATH
    else:
        catalog_path = USER_INSTALLER_DATA_PATH if path is None else path.expanduser().absolute()
    csv_path = COMMIT_DATE_REPORT_PATH if report_path is None else report_path.expanduser().absolute()
    if csv_path.resolve() == catalog_path.resolve():
        raise typer.BadParameter("CSV output must differ from the catalog path.", param_hint="--report-path")

    try:
        result = update_installer_commit_dates(path=catalog_path, report_path=csv_path, console=Console())
    except (OSError, InstallerDataFileError, RuntimeError) as error:
        typer.echo(f"""❌ {error}""", err=True)
        raise typer.Exit(code=1) from error

    typer.echo(f"""Updated {result.updated_installer_count}/{result.github_installer_count} GitHub software entries in {catalog_path}.""")
    typer.echo(f"""Saved {result.successful_repository_count}/{result.repository_count} repositories to {csv_path}.""")
    if result.failed_repository_count:
        typer.echo(f"""❌ {result.failed_repository_count} repositories failed; their existing metadata was retained.""", err=True)
        raise typer.Exit(code=1)
