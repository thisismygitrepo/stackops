import csv
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path

import pytest
from rich.console import Console

from stackops.utils.installer_utils import update_github_commit_dates
from stackops.utils.installer_utils.github_commit_dates_fetch import CommitDateFetchResult
from stackops.utils.installer_utils.github_commit_dates_report import RepositoryCommitDateFailure
from stackops.utils.installer_utils.installer_catalog import installer_data_file_text, load_installer_data_file
from stackops.utils.schemas.installer.installer_types import InstallerData


def _installer(app_name: str, repo_url: str) -> InstallerData:
    return {
        "appName": app_name,
        "license": "MIT",
        "repoURL": repo_url,
        "doc": f"{app_name} test entry",
        "categoryLabels": ["system-setup"],
        "fileNamePattern": {
            "amd64": {"linux": f"{app_name}.tar.gz", "darwin": None, "windows": None},
            "arm64": {"linux": None, "darwin": None, "windows": None},
        },
    }


def _write_catalog(path: Path, installers: list[InstallerData]) -> None:
    path.write_text(installer_data_file_text(path=path, catalog={"version": "4", "installers": installers}), encoding="utf-8")


def test_update_saves_installer_metadata_and_unique_repository_csv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    installer_data_path = tmp_path.joinpath("installer_data.yaml")
    stale_direct_installer = _installer(app_name="direct", repo_url="CMD")
    stale_direct_installer["lastCommitDate"] = "2020-01-01T00:00:00Z"
    stale_direct_installer["lastCommitDateCheckDate"] = "2020-01-02T00:00:00Z"
    _write_catalog(
        path=installer_data_path,
        installers=[
            _installer(app_name="first", repo_url="https://github.com/Owner/Repository"),
            _installer(app_name="duplicate", repo_url="https://github.com/owner/repository"),
            stale_direct_installer,
        ],
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

    saved_installers = load_installer_data_file(path=installer_data_path)["installers"]
    assert update_result == update_github_commit_dates.CommitDateUpdateResult(
        updated_installer_count=2, github_installer_count=2, successful_repository_count=1, failed_repository_count=0, repository_count=1
    )
    assert saved_installers[0]["lastCommitDate"] == "2026-08-15T12:30:45Z"
    assert saved_installers[1]["lastCommitDate"] == "2026-08-15T12:30:45Z"
    assert "lastCommitDate" not in saved_installers[2]
    assert "lastCommitDateCheckDate" not in saved_installers[2]
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
    installer_data_path = tmp_path.joinpath("installer_data.yaml")
    _write_catalog(path=installer_data_path, installers=[_installer(app_name="only", repo_url="https://github.com/owner/repository")])
    original_installer_data = installer_data_path.read_text(encoding="utf-8")
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
    installer_data_path = tmp_path.joinpath("installer_data.yaml")
    available_installer = _installer(app_name="available", repo_url="https://github.com/owner/available")
    available_installer["lastCommitDate"] = "2020-01-01T00:00:00Z"
    available_installer["lastCommitDateCheckDate"] = "2020-01-02T00:00:00Z"
    blocked_installer = _installer(app_name="blocked", repo_url="https://github.com/owner/blocked")
    blocked_installer["lastCommitDate"] = "2019-01-01T00:00:00Z"
    blocked_installer["lastCommitDateCheckDate"] = "2019-01-02T00:00:00Z"
    _write_catalog(path=installer_data_path, installers=[available_installer, blocked_installer])
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

    saved_installers = load_installer_data_file(path=installer_data_path)["installers"]
    assert update_result == update_github_commit_dates.CommitDateUpdateResult(
        updated_installer_count=1, github_installer_count=2, successful_repository_count=1, failed_repository_count=1, repository_count=2
    )
    assert saved_installers[0]["lastCommitDate"] == "2026-08-15T12:30:45Z"
    assert saved_installers[1] == blocked_installer
    report_rows = list(csv.reader(StringIO(report_path.read_text(encoding="utf-8"))))
    assert report_rows == [["repository", "last_commit_utc"], ["owner/available", "2026-08-15 12:30:45"]]
    rendered_output = output.getvalue()
    assert "1 fetch failures" in rendered_output
    assert "owner/blocked" in rendered_output
    assert "Repository access blocked" in rendered_output
