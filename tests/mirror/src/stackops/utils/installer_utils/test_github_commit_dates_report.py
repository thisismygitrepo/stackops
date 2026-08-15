import csv
from datetime import UTC, datetime
from io import StringIO

from rich.console import Console

from stackops.utils.installer_utils.github_commit_dates_report import (
    RepositoryCommitDate,
    build_fetched_commit_row,
    render_commit_date_extremes,
    serialize_commit_date_report,
    sort_repository_commit_dates,
)


def test_commit_date_report_is_newest_first_with_stable_repository_ties() -> None:
    repositories_by_key = {"owner/older": "owner/older", "owner/zeta": "owner/zeta", "owner/alpha": "owner/alpha"}
    commit_dates_by_repository_key = {
        "owner/older": datetime(2020, 1, 1, tzinfo=UTC),
        "owner/zeta": datetime(2026, 8, 15, tzinfo=UTC),
        "owner/alpha": datetime(2026, 8, 15, tzinfo=UTC),
    }

    sorted_commit_dates = sort_repository_commit_dates(
        repositories_by_key=repositories_by_key, commit_dates_by_repository_key=commit_dates_by_repository_key
    )
    report_text = serialize_commit_date_report(commit_dates=sorted_commit_dates)

    report_rows = list(csv.reader(StringIO(report_text)))
    assert report_rows == [
        ["repository", "last_commit_utc"],
        ["owner/alpha", "2026-08-15 00:00:00"],
        ["owner/zeta", "2026-08-15 00:00:00"],
        ["owner/older", "2020-01-01 00:00:00"],
    ]
    assert "\r" not in report_text


def test_fetched_commit_rows_align_human_readable_timestamps() -> None:
    output = StringIO()
    console = Console(file=output, width=120, color_system=None)
    repository_column_width = len("long-owner/long-repository")
    commit_dates = (
        RepositoryCommitDate(repository="a/b", last_commit_at=datetime(2026, 8, 15, 12, 30, 45, tzinfo=UTC)),
        RepositoryCommitDate(repository="long-owner/long-repository", last_commit_at=datetime(2020, 1, 2, 3, 4, 5, tzinfo=UTC)),
    )

    for commit_date in commit_dates:
        console.print(build_fetched_commit_row(commit_date=commit_date, repository_column_width=repository_column_width))

    rendered_lines = [line for line in output.getvalue().splitlines() if "20" in line]
    assert len(rendered_lines) == 2
    assert len({line.index("20") for line in rendered_lines}) == 1
    assert all("T" not in line and "Z" not in line for line in rendered_lines)


def test_commit_date_extremes_show_five_newest_and_five_oldest() -> None:
    commit_dates = [
        RepositoryCommitDate(repository=f"owner/repository-{year}", last_commit_at=datetime(year, 1, 1, tzinfo=UTC)) for year in range(2026, 2015, -1)
    ]
    output = StringIO()
    console = Console(file=output, width=120, color_system=None)

    render_commit_date_extremes(commit_dates=commit_dates, console=console)

    rendered_output = output.getvalue()
    newest_section, oldest_section = rendered_output.split("5 oldest commits")
    assert "5 newest commits" in newest_section
    assert "owner/repository-2026" in newest_section
    assert "owner/repository-2022" in newest_section
    assert "owner/repository-2021" not in newest_section
    assert "owner/repository-2016" in oldest_section
    assert "owner/repository-2020" in oldest_section
    assert "owner/repository-2021" not in oldest_section
    assert oldest_section.index("owner/repository-2016") < oldest_section.index("owner/repository-2020")
