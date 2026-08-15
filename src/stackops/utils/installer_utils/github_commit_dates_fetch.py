import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from time import monotonic
from urllib.parse import quote

from rich.console import Console
from rich.markup import escape
from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn

from stackops.utils.installer_utils.github_commit_dates_constants import GITHUB_HOST, MAX_CONCURRENT_GITHUB_REQUESTS
from stackops.utils.installer_utils.github_commit_dates_report import RepositoryCommitDate, build_fetched_commit_row


def run_gh(args: list[str], failure_message: str) -> str:
    try:
        result = subprocess.run(["gh", *args], check=False, capture_output=True, text=True)
    except FileNotFoundError as error:
        raise RuntimeError("GitHub CLI was not found on PATH. Install `gh`, then run `gh auth login --hostname github.com`.") from error
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or f"gh exited with code {result.returncode}"
        raise RuntimeError(f"{failure_message}\n{detail}")
    return result.stdout.strip()


def ensure_github_authentication() -> None:
    run_gh(
        args=["auth", "status", "--active", "--hostname", GITHUB_HOST],
        failure_message=("GitHub CLI is not logged in to github.com. Run `gh auth login --hostname github.com` and retry."),
    )


def fetch_last_commit_date(repository: str) -> datetime:
    owner, repo = repository.split("/", maxsplit=1)
    endpoint = f"repos/{quote(owner, safe='')}/{quote(repo, safe='')}/commits?per_page=1"
    last_commit_date_value = run_gh(
        args=["api", "--hostname", GITHUB_HOST, endpoint, "--jq", ".[0].commit.committer.date"],
        failure_message=f"Failed to fetch the latest commit for {repository}.",
    )
    if not last_commit_date_value:
        raise RuntimeError(f"GitHub returned no commits for {repository}.")
    try:
        last_commit_at = datetime.fromisoformat(last_commit_date_value)
    except ValueError as error:
        raise RuntimeError(f"GitHub returned an invalid commit timestamp for {repository}: {last_commit_date_value}") from error
    if last_commit_at.tzinfo is None or last_commit_at.utcoffset() is None:
        raise RuntimeError(f"GitHub returned a commit timestamp without a UTC offset for {repository}: {last_commit_date_value}")
    return last_commit_at.astimezone(UTC)


def fetch_commit_dates(repositories_by_key: dict[str, str], console: Console) -> dict[str, datetime]:
    repository_count = len(repositories_by_key)
    if repository_count == 0:
        return {}

    commit_dates_by_repository_key: dict[str, datetime] = {}
    failures: list[OSError | RuntimeError] = []
    worker_count = min(repository_count, MAX_CONCURRENT_GITHUB_REQUESTS)
    repository_column_width = max(len(repository) for repository in repositories_by_key.values())
    started_at = monotonic()
    completed_count = 0
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TextColumn("[cyan]{task.fields[rate]}"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    )

    with progress:
        executor = ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="github-commit-date")
        try:
            task_id = progress.add_task("Fetching latest commits", total=repository_count, rate="0.0 repos/s")
            future_to_repository = {
                executor.submit(fetch_last_commit_date, repository=repository): (repository_key, repository)
                for repository_key, repository in repositories_by_key.items()
            }
            for future in as_completed(future_to_repository):
                repository_key, repository = future_to_repository[future]
                try:
                    last_commit_at = future.result()
                except (OSError, RuntimeError) as error:
                    failures.append(error)
                    progress.console.print(f"[bold red]x[/bold red] {escape(repository)}  [red]{escape(str(error))}[/red]")
                else:
                    commit_dates_by_repository_key[repository_key] = last_commit_at
                    progress.console.print(
                        build_fetched_commit_row(
                            commit_date=RepositoryCommitDate(repository=repository, last_commit_at=last_commit_at),
                            repository_column_width=repository_column_width,
                        )
                    )

                completed_count += 1
                elapsed_seconds = monotonic() - started_at
                repositories_per_second = completed_count / elapsed_seconds
                progress.update(task_id, advance=1, rate=f"{repositories_per_second:.1f} repos/s")

            progress.update(
                task_id,
                description=("[bold red]Fetch completed with errors[/bold red]" if failures else "[bold green]Fetched latest commits[/bold green]"),
            )
        finally:
            executor.shutdown(wait=True, cancel_futures=True)

    if failures:
        raise RuntimeError(f"Failed to fetch {len(failures)} of {repository_count} repositories. First error:\n{failures[0]}") from failures[0]
    return commit_dates_by_repository_key
