from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from stackops.utils.installer_utils.github_commit_dates_constants import (
    COMMIT_DATE_REPORT_PATH,
    GITHUB_HOST,
    MAX_CONCURRENT_GITHUB_REQUESTS,
)
from stackops.utils.installer_utils.installer_catalog import (
    LIBRARY_INSTALLER_DATA_PATH,
    InstallerDataFileError,
    installer_data_file_text,
    load_installer_data_file,
)
from stackops.utils.installer_utils.github_commit_dates_fetch import ensure_github_authentication, fetch_commit_dates
from stackops.utils.installer_utils.github_commit_dates_output import TextOutput, commit_text_outputs
from stackops.utils.installer_utils.github_commit_dates_report import (
    render_commit_date_extremes,
    render_commit_date_failures,
    serialize_commit_date_report,
    sort_repository_commit_dates,
)


@dataclass(frozen=True, slots=True)
class CommitDateUpdateResult:
    updated_installer_count: int
    github_installer_count: int
    successful_repository_count: int
    failed_repository_count: int
    repository_count: int


def github_repository(repo_url: str) -> str | None:
    parsed_url = urlsplit(repo_url)
    if parsed_url.hostname not in {GITHUB_HOST, f"www.{GITHUB_HOST}"}:
        return None
    path_parts = [part for part in parsed_url.path.split("/") if part]
    if len(path_parts) != 2:
        raise RuntimeError(f"Expected a GitHub repository URL, received: {repo_url}")
    owner, repo = path_parts
    normalized_repo = repo.removesuffix(".git")
    return f"{owner}/{normalized_repo}"


def update_installer_commit_dates(path: Path, report_path: Path, console: Console) -> CommitDateUpdateResult:
    ensure_github_authentication()
    catalog = load_installer_data_file(path=path)
    installers = catalog["installers"]
    repositories_by_key: dict[str, str] = {}
    repository_keys_by_installer_index: dict[int, str] = {}

    for index, installer in enumerate(installers):
        repository = github_repository(repo_url=installer["repoURL"])
        if repository is None:
            continue
        repository_key = repository.casefold()
        repositories_by_key.setdefault(repository_key, repository)
        repository_keys_by_installer_index[index] = repository_key

    repository_count = len(repositories_by_key)
    github_installer_count = len(repository_keys_by_installer_index)
    refresh_summary = Table.grid(padding=(0, 2))
    refresh_summary.add_column(style="bold cyan", no_wrap=True)
    refresh_summary.add_column(overflow="fold")
    refresh_summary.add_row("GitHub installers", f"{github_installer_count} records across {repository_count} unique repositories")
    refresh_summary.add_row("Skipped", f"{len(installers) - github_installer_count} non-GitHub records")
    refresh_summary.add_row("Concurrency", f"up to {MAX_CONCURRENT_GITHUB_REQUESTS} requests")
    refresh_summary.add_row("Installer data", str(path))
    refresh_summary.add_row("CSV report", str(report_path))
    refresh_summary.add_row("Writes", "successful fetches are saved; failed repositories retain existing metadata")
    console.print(Panel.fit(refresh_summary, title="Refresh commit dates", border_style="blue"))
    fetch_result = fetch_commit_dates(repositories_by_key=repositories_by_key, console=console)
    commit_dates_by_repository_key = fetch_result.commit_dates_by_repository_key
    if repository_count > 0 and len(commit_dates_by_repository_key) == 0:
        raise RuntimeError(f"Failed to fetch all {repository_count} GitHub repositories; no outputs were written.")
    sorted_commit_dates = sort_repository_commit_dates(
        repositories_by_key=repositories_by_key, commit_dates_by_repository_key=commit_dates_by_repository_key
    )

    checked_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    for index, installer in enumerate(installers):
        installer_repository_key = repository_keys_by_installer_index.get(index)
        if installer_repository_key is None:
            installer.pop("lastCommitDate", None)
            installer.pop("lastCommitDateCheckDate", None)
        elif installer_repository_key in commit_dates_by_repository_key:
            installer["lastCommitDate"] = commit_dates_by_repository_key[installer_repository_key].isoformat(timespec="seconds").replace("+00:00", "Z")
            installer["lastCommitDateCheckDate"] = checked_at

    commit_text_outputs(
        outputs=(
            TextOutput(path=path, content=installer_data_file_text(path=path, catalog=catalog)),
            TextOutput(path=report_path, content=serialize_commit_date_report(commit_dates=sorted_commit_dates)),
        )
    )
    render_commit_date_extremes(commit_dates=sorted_commit_dates, console=console)
    render_commit_date_failures(failures=fetch_result.failures, console=console)
    updated_installer_count = sum(repository_key in commit_dates_by_repository_key for repository_key in repository_keys_by_installer_index.values())
    return CommitDateUpdateResult(
        updated_installer_count=updated_installer_count,
        github_installer_count=github_installer_count,
        successful_repository_count=len(commit_dates_by_repository_key),
        failed_repository_count=len(fetch_result.failures),
        repository_count=repository_count,
    )


def main() -> None:
    console = Console()
    try:
        update_result = update_installer_commit_dates(path=LIBRARY_INSTALLER_DATA_PATH, report_path=COMMIT_DATE_REPORT_PATH, console=console)
    except (OSError, InstallerDataFileError, RuntimeError) as error:
        raise SystemExit(str(error)) from error
    saved_summary = Table.grid(padding=(0, 2))
    saved_summary.add_column(style="bold cyan", no_wrap=True)
    saved_summary.add_column(overflow="fold")
    saved_summary.add_row(
        "Installer records", f"{update_result.updated_installer_count} updated of {update_result.github_installer_count} GitHub records"
    )
    saved_summary.add_row("Repositories saved", f"{update_result.successful_repository_count} of {update_result.repository_count}")
    saved_summary.add_row("Fetch failures", str(update_result.failed_repository_count))
    saved_summary.add_row("Installer data", str(LIBRARY_INSTALLER_DATA_PATH))
    saved_summary.add_row("CSV report", str(COMMIT_DATE_REPORT_PATH))
    panel_style = "yellow" if update_result.failed_repository_count > 0 else "green"
    panel_title = "Commit metadata saved with fetch failures" if update_result.failed_repository_count > 0 else "Commit metadata saved"
    console.print(Panel.fit(saved_summary, title=panel_title, border_style=panel_style))


if __name__ == "__main__":
    main()
