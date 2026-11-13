from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer

from stackops.utils.schemas.installer.installer_types import InstallerDataSource


def _parse_timestamp(value: str, context: str) -> datetime:
    from stackops.utils.installer_utils.installer_catalog import InstallerDataFileError

    try:
        timestamp = datetime.fromisoformat(value)
    except ValueError as error:
        raise InstallerDataFileError(f"""{context} must be an ISO timestamp with a timezone, got {value!r}""") from error
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise InstallerDataFileError(f"""{context} must include a timezone, got {value!r}""")
    return timestamp.astimezone(UTC)


def report(
    limit: Annotated[int, typer.Option("--limit", "-n", min=1, help="Number of GitHub software entries to show.")] = 10,
    reverse: Annotated[bool, typer.Option("--reverse", "-r", help="Show newest latest commits first instead of oldest first.")] = False,
    source: Annotated[
        InstallerDataSource,
        typer.Option("--source", "-s", help="Catalog: library, user, or all. User entries override matching library names."),
    ] = "all",
    path: Annotated[Path | None, typer.Option("--custom-path", "-p", help="Use another user catalog with --source user or all.")] = None,
) -> None:
    from rich.console import Console
    from rich.table import Table
    from rich.text import Text

    from stackops.utils.installer_utils.installer_catalog import InstallerDataFileError, read_installer_data
    from stackops.utils.installer_utils.update_github_commit_dates import github_repository

    rows: list[tuple[datetime, str, str, datetime | None]] = []
    missing: list[str] = []
    try:
        installers = read_installer_data(source=source, user_path=path)
        for installer in installers:
            repository = github_repository(repo_url=installer["repoURL"])
            if repository is None:
                continue
            app_name = installer["appName"]
            commit_value = installer.get("lastCommitDate")
            if commit_value is None:
                missing.append(app_name)
                continue
            last_commit = _parse_timestamp(value=commit_value, context=f"""{app_name}.lastCommitDate""")
            check_value = installer.get("lastCommitDateCheckDate")
            checked_at = None if check_value is None else _parse_timestamp(value=check_value, context=f"""{app_name}.lastCommitDateCheckDate""")
            rows.append((last_commit, app_name, repository, checked_at))
    except (InstallerDataFileError, RuntimeError) as error:
        typer.echo(f"""❌ {error}""", err=True)
        raise typer.Exit(code=1) from error

    console = Console()
    if not rows and not missing:
        console.print("No GitHub software found in the selected catalog.")
        return
    rows.sort(key=lambda row: row[1].casefold())
    rows.sort(key=lambda row: row[0], reverse=reverse)
    if rows:
        order = "Newest" if reverse else "Oldest"
        table = Table(title=f"""{order} latest commits ({source}, saved metadata; dates in UTC)""")
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Repository")
        table.add_column("Last commit", no_wrap=True)
        table.add_column("Days", justify="right", no_wrap=True)
        table.add_column("Checked", no_wrap=True)
        now = datetime.now(UTC)
        for last_commit, app_name, repository, checked_at in rows[:limit]:
            table.add_row(
                Text(app_name),
                Text(repository),
                f"""{last_commit:%Y-%m-%d}""",
                str((now - last_commit).days),
                "Unknown" if checked_at is None else f"""{checked_at:%Y-%m-%d}""",
            )
        console.print(table)
        console.print(f"""Showing {min(limit, len(rows))} of {len(rows)} GitHub software entries with saved commit dates.""")
    if missing:
        names = ", ".join(sorted(missing, key=str.casefold))
        console.print(Text(f"""Excluded {len(missing)} GitHub entries without saved commit dates: {names}."""))
    console.print("Run devops software update-attrs --source library (or --source user) to refresh the corresponding catalog.")
