from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_conflicts import MergeConflict


if TYPE_CHECKING:
    from git.repo import Repo
    from rich.console import Console


REMOTE_BRANCH_NAME = "master"


@dataclass(frozen=True)
class MergeSuccess:
    details: str


@dataclass(frozen=True)
class MergeConflictResult:
    details: str
    conflicts: tuple[MergeConflict, ...]


@dataclass(frozen=True)
class MergeGitError:
    details: str


type MergeAttemptResult = MergeSuccess | MergeConflictResult | MergeGitError


def _print_section(console: "Console", title: str) -> None:
    console.print("")
    console.print(f"[bold blue]═════ {title} ═════[/bold blue]")


def _has_staged_changes(repo: "Repo") -> bool:
    if repo.head.is_valid():
        return len(repo.index.diff("HEAD")) > 0
    return repo.git.diff("--cached", "--name-only").strip() != ""


def commit_local_changes(repo: "Repo", message: str, console: "Console") -> None:
    _print_section(console=console, title="COMMITTING LOCAL CHANGES")
    print(repo.git.status())
    repo.git.add(A=True)
    if not _has_staged_changes(repo=repo):
        print("-> No staged changes to commit.")
        return
    repo.git.diff("--cached", "--check")
    commit_output = repo.git.commit(m=message)
    if commit_output.strip() != "":
        print(commit_output)


def merge_remote_copy(repo: "Repo", remote_path: Path, console: "Console") -> MergeAttemptResult:
    from git.exc import GitCommandError

    from stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_conflicts import get_merge_conflicts

    _print_section(console=console, title="INTEGRATING LATEST REMOTE COMMIT")
    try:
        repo.git.fetch(str(remote_path), REMOTE_BRANCH_NAME)
        merge_output = repo.git.merge("FETCH_HEAD", no_edit=True)
    except GitCommandError as exc:
        conflicts = get_merge_conflicts(repo=repo)
        if len(conflicts) > 0:
            return MergeConflictResult(details=str(exc), conflicts=conflicts)
        return MergeGitError(details=str(exc))
    conflicts = get_merge_conflicts(repo=repo)
    if len(conflicts) > 0:
        return MergeConflictResult(details="Merge finished but the integration worktree still contains unresolved paths.", conflicts=conflicts)
    return MergeSuccess(details=merge_output)
