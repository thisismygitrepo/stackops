import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict, cast
from urllib.parse import urlsplit

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from stackops.utils.installer_utils.github_commit_dates_constants import (
    COMMIT_DATE_REPORT_PATH,
    GITHUB_HOST,
    INSTALLER_DATA_PATH,
    MAX_CONCURRENT_GITHUB_REQUESTS,
)
from stackops.utils.installer_utils.github_commit_dates_fetch import ensure_github_authentication, fetch_commit_dates
from stackops.utils.installer_utils.github_commit_dates_output import TextOutput, commit_text_outputs
from stackops.utils.installer_utils.github_commit_dates_report import (
    render_commit_date_extremes,
    serialize_commit_date_report,
    sort_repository_commit_dates,
)


class CommitDateMetadata(TypedDict):
    lastCommitDate: str
    lastCommitDateCheckDate: str


def require_json_object(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise RuntimeError(f"Expected {context} to be a JSON object.")
    return cast(dict[str, object], value)


def load_installer_data(path: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    payload_value: object = json.loads(path.read_text(encoding="utf-8"))
    payload = require_json_object(value=payload_value, context=str(path))
    installers_value = payload.get("installers")
    if not isinstance(installers_value, list):
        raise RuntimeError(f"Expected {path} to contain an 'installers' array.")
    installers = [require_json_object(value=installer, context=f"installers[{index}]") for index, installer in enumerate(installers_value)]
    return payload, installers


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


def update_installer_commit_dates(path: Path, report_path: Path, console: Console) -> tuple[int, int]:
    ensure_github_authentication()
    payload, installers = load_installer_data(path=path)
    repositories_by_key: dict[str, str] = {}
    repository_keys_by_installer_index: dict[int, str] = {}

    for index, installer in enumerate(installers):
        repo_url = installer.get("repoURL")
        if not isinstance(repo_url, str):
            raise RuntimeError(f"Expected installers[{index}].repoURL to be a string.")
        repository = github_repository(repo_url=repo_url)
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
    refresh_summary.add_row("Writes", "once all GitHub requests succeed")
    console.print(Panel.fit(refresh_summary, title="Refresh commit dates", border_style="blue"))
    commit_dates_by_repository_key = fetch_commit_dates(repositories_by_key=repositories_by_key, console=console)
    sorted_commit_dates = sort_repository_commit_dates(
        repositories_by_key=repositories_by_key, commit_dates_by_repository_key=commit_dates_by_repository_key
    )

    checked_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    for index, installer in enumerate(installers):
        repository_key = repository_keys_by_installer_index.get(index)
        updated_installer = {key: value for key, value in installer.items() if key not in {"lastCommitDate", "lastCommitDateCheckDate"}}
        if repository_key is not None:
            metadata = CommitDateMetadata(
                lastCommitDate=commit_dates_by_repository_key[repository_key].isoformat(timespec="seconds").replace("+00:00", "Z"),
                lastCommitDateCheckDate=checked_at,
            )
            ordered_installer: dict[str, object] = {}
            for key, value in updated_installer.items():
                ordered_installer[key] = value
                if key == "repoURL":
                    ordered_installer.update(metadata)
            updated_installer = ordered_installer
        installers[index] = updated_installer

    payload["installers"] = installers
    commit_text_outputs(
        outputs=(
            TextOutput(path=path, content=json.dumps(payload, indent=2, ensure_ascii=False) + "\n"),
            TextOutput(path=report_path, content=serialize_commit_date_report(commit_dates=sorted_commit_dates)),
        )
    )
    render_commit_date_extremes(commit_dates=sorted_commit_dates, console=console)
    return github_installer_count, repository_count


def main() -> None:
    console = Console()
    try:
        updated_count, repository_count = update_installer_commit_dates(
            path=INSTALLER_DATA_PATH, report_path=COMMIT_DATE_REPORT_PATH, console=console
        )
    except (OSError, json.JSONDecodeError, RuntimeError) as error:
        raise SystemExit(str(error)) from error
    saved_summary = Table.grid(padding=(0, 2))
    saved_summary.add_column(style="bold cyan", no_wrap=True)
    saved_summary.add_column(overflow="fold")
    saved_summary.add_row("Installer records", str(updated_count))
    saved_summary.add_row("Unique repositories", str(repository_count))
    saved_summary.add_row("Installer data", str(INSTALLER_DATA_PATH))
    saved_summary.add_row("CSV report", str(COMMIT_DATE_REPORT_PATH))
    console.print(Panel.fit(saved_summary, title="Commit metadata saved", border_style="green"))


if __name__ == "__main__":
    main()
