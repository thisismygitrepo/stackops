import csv
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from io import StringIO

from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from stackops.utils.installer_utils.github_commit_dates_constants import (
    COMMIT_DATE_DISPLAY_FORMAT,
    COMMIT_DATE_EXTREME_COUNT,
    COMMIT_DATE_REPORT_COLUMNS,
)


@dataclass(frozen=True, slots=True)
class RepositoryCommitDate:
    repository: str
    last_commit_at: datetime


def sort_repository_commit_dates(
    repositories_by_key: dict[str, str], commit_dates_by_repository_key: dict[str, datetime]
) -> list[RepositoryCommitDate]:
    commit_dates = [
        RepositoryCommitDate(repository=repositories_by_key[repository_key], last_commit_at=last_commit_at)
        for repository_key, last_commit_at in commit_dates_by_repository_key.items()
    ]
    commit_dates.sort(key=lambda commit_date: commit_date.repository.casefold())
    commit_dates.sort(key=lambda commit_date: commit_date.last_commit_at, reverse=True)
    return commit_dates


def build_fetched_commit_row(commit_date: RepositoryCommitDate, repository_column_width: int) -> Table:
    row = Table.grid(padding=(0, 2))
    row.add_column(width=1, no_wrap=True)
    row.add_column(width=repository_column_width, no_wrap=True)
    row.add_column(no_wrap=True)
    row.add_row(
        Text("✓", style="bold green"),
        Text(commit_date.repository),
        Text(commit_date.last_commit_at.strftime(COMMIT_DATE_DISPLAY_FORMAT), style="cyan"),
    )
    return row


def serialize_commit_date_report(commit_dates: Sequence[RepositoryCommitDate]) -> str:
    report_buffer = StringIO(newline="")
    report_writer = csv.writer(report_buffer, lineterminator="\n")
    report_writer.writerow(COMMIT_DATE_REPORT_COLUMNS)
    report_writer.writerows((commit_date.repository, commit_date.last_commit_at.strftime(COMMIT_DATE_DISPLAY_FORMAT)) for commit_date in commit_dates)
    return report_buffer.getvalue()


def build_commit_date_table(title: str, commit_dates: Sequence[RepositoryCommitDate], repository_column_width: int) -> Table:
    table = Table(title=title, box=box.SIMPLE_HEAVY, header_style="bold cyan", expand=False)
    table.add_column("Repository", style="cyan", width=repository_column_width, no_wrap=True)
    table.add_column("Last commit (UTC)", justify="right", no_wrap=True)
    for commit_date in commit_dates:
        table.add_row(commit_date.repository, commit_date.last_commit_at.strftime(COMMIT_DATE_DISPLAY_FORMAT))
    return table


def render_commit_date_extremes(commit_dates: Sequence[RepositoryCommitDate], console: Console) -> None:
    if len(commit_dates) == 0:
        return
    repository_column_width = max(len(commit_date.repository) for commit_date in commit_dates)
    newest_commit_dates = commit_dates[:COMMIT_DATE_EXTREME_COUNT]
    oldest_commit_dates = tuple(reversed(commit_dates[-COMMIT_DATE_EXTREME_COUNT:]))
    console.print(
        build_commit_date_table(
            title=f"{len(newest_commit_dates)} newest commits", commit_dates=newest_commit_dates, repository_column_width=repository_column_width
        )
    )
    console.print(
        build_commit_date_table(
            title=f"{len(oldest_commit_dates)} oldest commits", commit_dates=oldest_commit_dates, repository_column_width=repository_column_width
        )
    )
