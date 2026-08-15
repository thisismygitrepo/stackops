import csv
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path

import pytest
from rich.console import Console

from stackops.utils.installer_utils import update_github_commit_dates
from stackops.utils.installer_utils.github_commit_dates_fetch import CommitDateFetchResult
from stackops.utils.installer_utils.github_commit_dates_report import RepositoryCommitDateFailure


def test_update_saves_installer_metadata_and_unique_repository_csv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    installer_data_path = tmp_path.joinpath("installer_data.json")
    installer_data_path.write_text(
        """{
  "installers": [
    {"appName": "first", "repoURL": "https://github.com/Owner/Repository"},
    {"appName": "duplicate", "repoURL": "https://github.com/owner/repository"},
    {"appName": "direct", "repoURL": "CMD"}
  ]
}
""",
        encoding="utf-8",
    )
    report_path = tmp_path.joinpath("profile", "records", "github_commit_dates.csv")
    output = StringIO()
    render_console = Console(file=output, width=160, color_system=None)

    def authenticate() -> None:
        assert installer_data_path.is_file()

    def fetch_dates(repositories_by_key: dict[str, str], console: Console) -> CommitDateFetchResult:
        assert repositories_by_key == {"owner/repository": "Owner/Repository"}
        assert console is render_console
        return CommitDateFetchResult(commit_dates_by_repository_key={"owner/repository": datetime(2026, 8, 15, 12, 30, 45, tzinfo=UTC)}, failures=())

    monkeypatch.setattr(update_github_commit_dates, "ensure_github_authentication", authenticate)
    monkeypatch.setattr(update_github_commit_dates, "fetch_commit_dates", fetch_dates)

    update_result = update_github_commit_dates.update_installer_commit_dates(
        path=installer_data_path, report_path=report_path, console=render_console
    )

    _, saved_installers = update_github_commit_dates.load_installer_data(path=installer_data_path)
    assert update_result == update_github_commit_dates.CommitDateUpdateResult(
        updated_installer_count=2, github_installer_count=2, successful_repository_count=1, failed_repository_count=0, repository_count=1
    )
    assert saved_installers[0]["lastCommitDate"] == "2026-08-15T12:30:45Z"
    assert saved_installers[1]["lastCommitDate"] == "2026-08-15T12:30:45Z"
    assert "lastCommitDate" not in saved_installers[2]
    for saved_installer in saved_installers[:2]:
        checked_at = saved_installer["lastCommitDateCheckDate"]
        assert isinstance(checked_at, str)
        assert checked_at.endswith("Z")
        assert "T" in checked_at

    report_rows = list(csv.reader(StringIO(report_path.read_text(encoding="utf-8"))))
    assert report_rows == [["repository", "last_commit_utc"], ["Owner/Repository", "2026-08-15 12:30:45"]]
    rendered_output = output.getvalue()
    assert str(installer_data_path) in rendered_output
    assert str(report_path) in rendered_output
    assert "successful fetches are saved" in rendered_output


def test_all_fetches_failing_leaves_outputs_untouched(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    installer_data_path = tmp_path.joinpath("installer_data.json")
    original_installer_data = """{"installers": [{"repoURL": "https://github.com/owner/repository"}]}\n"""
    installer_data_path.write_text(original_installer_data, encoding="utf-8")
    report_path = tmp_path.joinpath("reports", "github_commit_dates.csv")
    render_console = Console(file=StringIO(), width=120, color_system=None)

    def authenticate() -> None:
        assert installer_data_path.is_file()

    def fail_fetch(repositories_by_key: dict[str, str], console: Console) -> CommitDateFetchResult:
        assert repositories_by_key == {"owner/repository": "owner/repository"}
        assert console is render_console
        return CommitDateFetchResult(
            commit_dates_by_repository_key={},
            failures=(RepositoryCommitDateFailure(repository="owner/repository", error_message="GitHub unavailable"),),
        )

    monkeypatch.setattr(update_github_commit_dates, "ensure_github_authentication", authenticate)
    monkeypatch.setattr(update_github_commit_dates, "fetch_commit_dates", fail_fetch)

    with pytest.raises(RuntimeError, match="Failed to fetch all 1 GitHub repositories"):
        update_github_commit_dates.update_installer_commit_dates(path=installer_data_path, report_path=report_path, console=render_console)

    assert installer_data_path.read_text(encoding="utf-8") == original_installer_data
    assert not report_path.exists()


def test_partial_fetch_saves_successes_and_preserves_failed_metadata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    installer_data_path = tmp_path.joinpath("installer_data.json")
    installer_data_path.write_text(
        """{
  "installers": [
    {
      "appName": "available",
      "repoURL": "https://github.com/owner/available",
      "lastCommitDate": "2020-01-01T00:00:00Z",
      "lastCommitDateCheckDate": "2020-01-02T00:00:00Z"
    },
    {
      "appName": "blocked",
      "repoURL": "https://github.com/owner/blocked",
      "lastCommitDate": "2019-01-01T00:00:00Z",
      "lastCommitDateCheckDate": "2019-01-02T00:00:00Z"
    }
  ]
}
""",
        encoding="utf-8",
    )
    report_path = tmp_path.joinpath("records", "github_commit_dates.csv")
    output = StringIO()
    render_console = Console(file=output, width=160, color_system=None)

    def authenticate() -> None:
        assert installer_data_path.is_file()

    def fetch_dates(repositories_by_key: dict[str, str], console: Console) -> CommitDateFetchResult:
        assert repositories_by_key == {"owner/available": "owner/available", "owner/blocked": "owner/blocked"}
        assert console is render_console
        return CommitDateFetchResult(
            commit_dates_by_repository_key={"owner/available": datetime(2026, 8, 15, 12, 30, 45, tzinfo=UTC)},
            failures=(RepositoryCommitDateFailure(repository="owner/blocked", error_message="Repository access blocked"),),
        )

    monkeypatch.setattr(update_github_commit_dates, "ensure_github_authentication", authenticate)
    monkeypatch.setattr(update_github_commit_dates, "fetch_commit_dates", fetch_dates)

    update_result = update_github_commit_dates.update_installer_commit_dates(
        path=installer_data_path, report_path=report_path, console=render_console
    )

    _, saved_installers = update_github_commit_dates.load_installer_data(path=installer_data_path)
    assert update_result == update_github_commit_dates.CommitDateUpdateResult(
        updated_installer_count=1, github_installer_count=2, successful_repository_count=1, failed_repository_count=1, repository_count=2
    )
    assert saved_installers[0]["lastCommitDate"] == "2026-08-15T12:30:45Z"
    assert saved_installers[1] == {
        "appName": "blocked",
        "repoURL": "https://github.com/owner/blocked",
        "lastCommitDate": "2019-01-01T00:00:00Z",
        "lastCommitDateCheckDate": "2019-01-02T00:00:00Z",
    }
    report_rows = list(csv.reader(StringIO(report_path.read_text(encoding="utf-8"))))
    assert report_rows == [["repository", "last_commit_utc"], ["owner/available", "2026-08-15 12:30:45"]]
    rendered_output = output.getvalue()
    assert "1 fetch failures" in rendered_output
    assert "owner/blocked" in rendered_output
    assert "Repository access blocked" in rendered_output
