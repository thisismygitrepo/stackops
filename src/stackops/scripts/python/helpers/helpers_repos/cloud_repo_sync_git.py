from dataclasses import dataclass
import os
from pathlib import Path
import stat
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


def restore_downloaded_file_modes(repo: "Repo") -> None:
    if os.name == "nt":
        repo.git.config("--local", "core.filemode", "false")
        return

    repo_root = Path(repo.working_dir)
    executable_bits = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
    for (relative_path, stage), entry in repo.index.entries.items():
        if stage != 0 or not stat.S_ISREG(entry.mode):
            continue
        file_path = repo_root.joinpath(relative_path)
        if not file_path.is_file(follow_symlinks=False):
            continue
        current_mode = stat.S_IMODE(file_path.stat(follow_symlinks=False).st_mode)
        restored_mode = (current_mode & ~executable_bits) | (entry.mode & executable_bits)
        if restored_mode != current_mode:
            file_path.chmod(restored_mode)
    repo.git.config("--local", "core.filemode", "true")


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
