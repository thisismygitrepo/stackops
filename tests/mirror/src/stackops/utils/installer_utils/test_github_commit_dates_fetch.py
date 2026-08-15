from datetime import UTC, datetime
from io import StringIO

import pytest
from rich.console import Console

from stackops.utils.installer_utils import github_commit_dates_fetch
from stackops.utils.installer_utils.github_commit_dates_report import RepositoryCommitDateFailure


def test_fetch_last_commit_date_parses_and_normalizes_utc(monkeypatch: pytest.MonkeyPatch) -> None:
    def return_offset_timestamp(args: list[str], failure_message: str) -> str:
        assert args[0] == "api"
        assert failure_message == "Failed to fetch the latest commit for owner/repository."
        return "2026-08-15T14:30:00+02:00"

    monkeypatch.setattr(github_commit_dates_fetch, "run_gh", return_offset_timestamp)

    last_commit_at = github_commit_dates_fetch.fetch_last_commit_date("owner/repository")

    assert last_commit_at == datetime(2026, 8, 15, 12, 30, tzinfo=UTC)
    assert last_commit_at.tzinfo is UTC


@pytest.mark.parametrize("timestamp", ("not-a-timestamp", "2026-08-15T12:30:00"))
def test_fetch_last_commit_date_rejects_invalid_or_naive_timestamps(timestamp: str, monkeypatch: pytest.MonkeyPatch) -> None:
    def return_invalid_timestamp(args: list[str], failure_message: str) -> str:
        assert args[0] == "api"
        assert failure_message == "Failed to fetch the latest commit for owner/repository."
        return timestamp

    monkeypatch.setattr(github_commit_dates_fetch, "run_gh", return_invalid_timestamp)

    with pytest.raises(RuntimeError, match="invalid commit timestamp|without a UTC offset"):
        github_commit_dates_fetch.fetch_last_commit_date("owner/repository")


def test_fetch_commit_dates_returns_successes_and_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    def fetch_repository(repository: str) -> datetime:
        if repository == "owner/blocked":
            raise RuntimeError("Repository access blocked")
        assert repository == "owner/available"
        return datetime(2026, 8, 15, 12, 30, tzinfo=UTC)

    monkeypatch.setattr(github_commit_dates_fetch, "fetch_last_commit_date", fetch_repository)
    console = Console(file=StringIO(), width=120, color_system=None)

    result = github_commit_dates_fetch.fetch_commit_dates(
        repositories_by_key={"owner/available": "owner/available", "owner/blocked": "owner/blocked"}, console=console
    )

    assert result.commit_dates_by_repository_key == {"owner/available": datetime(2026, 8, 15, 12, 30, tzinfo=UTC)}
    assert result.failures == (RepositoryCommitDateFailure(repository="owner/blocked", error_message="Repository access blocked"),)
