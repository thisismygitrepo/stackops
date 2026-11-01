from dataclasses import dataclass
import os
from pathlib import Path
import stat
import sys
from typing import TYPE_CHECKING

from stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_conflicts import MergeConflict


if TYPE_CHECKING:
    from git.repo import Repo
    from rich.console import Console


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


def prepare_downloaded_repository(repo: "Repo") -> None:
    repo.git.config("--local", "core.autocrlf", "input")
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


def _has_git_identity(repo: "Repo") -> bool:
    from git.exc import GitCommandError

    with repo.git.custom_environment(LC_ALL="C"):
        for identity in ("GIT_AUTHOR_IDENT", "GIT_COMMITTER_IDENT"):
            try:
                repo.git.var(identity)
            except GitCommandError as error:
                if any(reason in error.stderr.lower() for reason in (
                    "identity unknown", "unable to auto-detect email address", "empty ident name", "empty ident email",
                    "no name was given", "no email was given",
                )):
                    return False
                raise
    return True


def ensure_git_identity(repo: "Repo", console: "Console") -> None:
    from git.exc import GitCommandError
    import typer

    if _has_git_identity(repo=repo):
        return
    console.print("Git needs your name and email before it can commit. These details will be saved only for this repository.")
    if not sys.stdin.isatty():
        console.print("Run guard in an interactive terminal to enter your Git name and email, or configure user.name and user.email for this repository.")
        raise typer.Exit(code=1)

    values: dict[str, str] = {}
    for field, label in (("name", "Git name"), ("email", "Git email")):
        try:
            current_value = repo.git.config("--get", f"""user.{field}""").strip()
        except GitCommandError as error:
            if error.status != 1:
                raise
            current_value = ""
        while True:
            try:
                value = str(typer.prompt(label, default=current_value or None, type=str)).strip()
            except (typer.Abort, EOFError, KeyboardInterrupt):
                console.print("Git identity setup cancelled. Guard stopped without creating a commit.")
                raise typer.Exit(code=1) from None
            if value and not any(character in value for character in "\0\r\n<>"):
                values[field] = value
                break
            console.print("Enter a nonempty value without angle brackets or line breaks.")

    for field, value in values.items():
        repo.git.config("--local", "--replace-all", f"""user.{field}""", value)
    if not _has_git_identity(repo=repo):
        console.print("Git still cannot use this identity. Check GIT_AUTHOR_NAME, GIT_AUTHOR_EMAIL, GIT_COMMITTER_NAME and GIT_COMMITTER_EMAIL in your environment.")
        raise typer.Exit(code=1)


def commit_local_changes(repo: "Repo", message: str, console: "Console") -> None:
    _print_section(console=console, title="COMMITTING LOCAL CHANGES")
    print(repo.git.status())
    repo.git.add(A=True)
    if not _has_staged_changes(repo=repo):
        print("-> No staged changes to commit.")
        return
    ensure_git_identity(repo=repo, console=console)
    commit_output = repo.git.commit(m=message)
    if commit_output.strip() != "":
        print(commit_output)


def merge_remote_copy(repo: "Repo", remote_path: Path, console: "Console") -> MergeAttemptResult:
    from git.exc import GitCommandError

    from stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_conflicts import get_merge_conflicts
    from stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_status import print_repository_comparison

    _print_section(console=console, title="INTEGRATING LATEST REMOTE COMMIT")
    try:
        repo.git.fetch("--no-recurse-submodules", str(remote_path), "HEAD")
        print_repository_comparison(
            repo=repo, local_commit=repo.head.commit, remote_commit=repo.commit("FETCH_HEAD"),
            console=console, title="Before integration",
        )
        ensure_git_identity(repo=repo, console=console)
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
