from dataclasses import dataclass
from pathlib import Path
from typing import assert_never, cast

from git.exc import InvalidGitRepositoryError
from git.repo import Repo

from stackops.scripts.python.helpers.helpers_repos.action_helper import GitAction, GitOperationResult
from stackops.scripts.python.helpers.helpers_repos.update import update_repository


@dataclass(frozen=True, slots=True)
class OperationContext:
    repo_path: Path
    action: GitAction
    remote_count: int
    dry_run: bool


def _result(context: OperationContext, *, success: bool, message: str, is_git_repo: bool, had_changes: bool) -> GitOperationResult:
    return GitOperationResult(
        repo_path=context.repo_path,
        action=context.action,
        success=success,
        message=message,
        is_git_repo=is_git_repo,
        had_changes=had_changes,
        remote_count=context.remote_count,
        dry_run=context.dry_run,
    )


def _status(repo: Repo, context: OperationContext) -> GitOperationResult:
    status_output = cast(str, repo.git.status("--short", "--branch")).strip()
    return _result(context, success=True, message=status_output, is_git_repo=True, had_changes=repo.is_dirty(untracked_files=True))


def _pull(repo: Repo, context: OperationContext, auto_uv_sync: bool) -> GitOperationResult:
    if context.dry_run:
        if not repo.remotes:
            return _result(context, success=False, message="No remotes configured", is_git_repo=True, had_changes=False)
        remote_names = ", ".join(remote.name for remote in repo.remotes)
        detail = f"Would pull {repo.active_branch.name} from: {remote_names}"
        return _result(context, success=True, message=detail, is_git_repo=True, had_changes=False)

    update = update_repository(repo, auto_uv_sync=auto_uv_sync, allow_password_prompt=False)
    if update["status"] != "success":
        detail = update["error_message"] or f"Pull finished with status: {update['status']}"
        return _result(context, success=False, message=detail, is_git_repo=True, had_changes=False)
    detail = f"Updated {update['commit_before'][:8]} → {update['commit_after'][:8]}" if update["commits_changed"] else "Already up to date"
    if update["uv_sync_ran"]:
        detail = f"{detail}; uv sync completed"
    return _result(context, success=True, message=detail, is_git_repo=True, had_changes=update["commits_changed"])


def _commit(repo: Repo, context: OperationContext, message: str | None) -> GitOperationResult:
    if message is None or not message.strip():
        return _result(context, success=False, message="A non-empty commit message is required", is_git_repo=True, had_changes=False)
    staged_files = cast(str, repo.git.diff("--cached", "--name-only")).splitlines()
    if not staged_files:
        if repo.is_dirty(untracked_files=True):
            detail = "No staged changes; stage files explicitly before using --commit"
            return _result(context, success=False, message=detail, is_git_repo=True, had_changes=False)
        return _result(context, success=True, message="No changes to commit", is_git_repo=True, had_changes=False)

    staged_file_list = ", ".join(staged_files)
    if context.dry_run:
        detail = f"Would commit staged files with message {message!r}: {staged_file_list}"
        return _result(context, success=True, message=detail, is_git_repo=True, had_changes=True)
    repo.index.commit(message)
    detail = f"Committed staged files with message {message!r}: {staged_file_list}"
    return _result(context, success=True, message=detail, is_git_repo=True, had_changes=True)


def _push(repo: Repo, context: OperationContext) -> GitOperationResult:
    if not repo.remotes:
        return _result(context, success=False, message="No remotes configured", is_git_repo=True, had_changes=False)
    branch_name = repo.active_branch.name
    remote_names = [remote.name for remote in repo.remotes]
    if context.dry_run:
        detail = f"Would push {branch_name} to: {', '.join(remote_names)}"
        return _result(context, success=True, message=detail, is_git_repo=True, had_changes=False)

    failed_remotes: list[str] = []
    for remote in repo.remotes:
        try:
            push_results = remote.push(branch_name)
            if len(push_results) == 0:
                raise RuntimeError("push returned no result")
            push_results.raise_if_error()
        except Exception as error:
            failed_remotes.append(f"{remote.name}: {error}")
    if failed_remotes:
        return _result(context, success=False, message="; ".join(failed_remotes), is_git_repo=True, had_changes=False)
    detail = f"Pushed {branch_name} to: {', '.join(remote_names)}"
    return _result(context, success=True, message=detail, is_git_repo=True, had_changes=False)


def git_action(path: Path, action: GitAction, message: str | None, auto_uv_sync: bool, dry_run: bool) -> GitOperationResult:
    context = OperationContext(repo_path=path, action=action, remote_count=0, dry_run=dry_run)
    try:
        repo = Repo(path, search_parent_directories=False)
    except InvalidGitRepositoryError:
        return _result(context, success=False, message="Not a git repository", is_git_repo=False, had_changes=False)

    context = OperationContext(repo_path=path, action=action, remote_count=len(repo.remotes), dry_run=dry_run)
    try:
        match action:
            case GitAction.status:
                return _status(repo=repo, context=context)
            case GitAction.pull:
                return _pull(repo=repo, context=context, auto_uv_sync=auto_uv_sync)
            case GitAction.commit:
                return _commit(repo=repo, context=context, message=message)
            case GitAction.push:
                return _push(repo=repo, context=context)
        assert_never(action)
    except Exception as error:
        return _result(context, success=False, message=str(error), is_git_repo=True, had_changes=False)
