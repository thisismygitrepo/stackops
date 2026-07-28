import concurrent.futures
import os
from pathlib import Path
from typing import TypedDict, assert_never, cast

from git.exc import InvalidGitRepositoryError
from git.repo import Repo
from rich import print as pprint

from stackops.scripts.python.helpers.helpers_repos.action_helper import (
    GitAction,
    GitOperationResult,
    GitOperationSummary,
    print_git_operations_summary,
)
from stackops.scripts.python.helpers.helpers_repos.update import update_repository
from stackops.utils.accessories import randstr


class RepositoryOperationPayload(TypedDict):
    path: Path
    is_git: bool
    results: list[GitOperationResult]
    repo_remotes_count: int


def _repository_candidates(repos_root: Path, recursive: bool) -> list[Path]:
    try:
        Repo(repos_root, search_parent_directories=False)
    except InvalidGitRepositoryError:
        pass
    else:
        return [repos_root]

    if not recursive:
        return list(repos_root.glob("*"))

    repository_paths: list[Path] = []
    for current_root, directory_names, file_names in os.walk(repos_root):
        current_path = Path(current_root)
        if ".git" in directory_names or ".git" in file_names:
            repository_paths.append(current_path)
            directory_names.clear()
            continue
        directory_names[:] = [name for name in directory_names if not name.startswith(".")]
    return repository_paths


def git_action(path: Path, action: GitAction, message: str | None, auto_uv_sync: bool) -> GitOperationResult:
    try:
        repo = Repo(path, search_parent_directories=False)
    except InvalidGitRepositoryError:
        pprint(f"⚠️ Skipping {path} because it is not a git repository.")
        return GitOperationResult(repo_path=path, action=action, success=False, message="Not a git repository", is_git_repo=False)

    print(f">>>>>>>>> 🔧 {action.value} - {path}")
    remote_count = len(repo.remotes)

    try:
        match action:
            case GitAction.status:
                status_output = cast(str, repo.git.status("--short", "--branch")).strip()
                has_changes = repo.is_dirty(untracked_files=True)
                print(status_output)
                return GitOperationResult(
                    repo_path=path, action=action, success=True, message=status_output, had_changes=has_changes, remote_count=remote_count
                )
            case GitAction.commit:
                commit_message = message or f"auto_commit_{randstr()}"
                if not repo.is_dirty(untracked_files=True):
                    print("ℹ️  No changes to commit")
                    return GitOperationResult(
                        repo_path=path, action=action, success=True, message="No changes to commit", had_changes=False, remote_count=remote_count
                    )
                repo.git.add(A=True)
                repo.index.commit(commit_message)
                print(f"✅ Committed changes with message: {commit_message}")
                return GitOperationResult(
                    repo_path=path,
                    action=action,
                    success=True,
                    message=f"Committed changes with message: {commit_message}",
                    had_changes=True,
                    remote_count=remote_count,
                )
            case GitAction.push:
                if not repo.remotes:
                    print("⚠️ No remotes configured for push")
                    return GitOperationResult(repo_path=path, action=action, success=False, message="No remotes configured", remote_count=0)
                failed_remotes: list[str] = []
                for remote in repo.remotes:
                    try:
                        print(f"🚀 Pushing to {remote.url}")
                        remote.push(repo.active_branch.name)
                        print(f"✅ Pushed to {remote.name}")
                    except Exception as error:
                        print(f"❌ Failed to push to {remote.name}: {error}")
                        failed_remotes.append(f"{remote.name}: {error}")
                success = not failed_remotes
                push_message = "Push successful" if success else f"Push failed for: {', '.join(failed_remotes)}"
                return GitOperationResult(repo_path=path, action=action, success=success, message=push_message, remote_count=remote_count)
            case GitAction.pull:
                update_repository(repo, auto_uv_sync=auto_uv_sync, allow_password_prompt=False)
                print("✅ Pull completed")
                return GitOperationResult(
                    repo_path=path, action=action, success=True, message="Pull completed successfully", remote_count=remote_count
                )
        assert_never(action)
    except Exception as error:
        print(f"❌ Error performing {action.value} on {path}: {error}")
        return GitOperationResult(repo_path=path, action=action, success=False, message=f"Error: {error}", remote_count=remote_count)


def _process_repository_path(path: Path, actions: tuple[GitAction, ...], auto_uv_sync: bool) -> RepositoryOperationPayload:
    print(f"{('Handling ' + str(path)).center(80, '-')}")
    try:
        repo = Repo(path, search_parent_directories=False)
    except InvalidGitRepositoryError:
        pprint(f"⚠️ Skipping {path} because it is not a git repository.")
        return {"path": path, "is_git": False, "results": [], "repo_remotes_count": 0}

    results = [git_action(path=path, action=action, message=None, auto_uv_sync=auto_uv_sync) for action in actions]
    return {"path": path, "is_git": True, "results": results, "repo_remotes_count": len(repo.remotes)}


def _record_result(summary: GitOperationSummary, result: GitOperationResult) -> None:
    match result.action:
        case GitAction.status:
            summary.statuses_attempted += 1
            summary.status_results.append(result)
            if result.success and result.had_changes:
                summary.statuses_with_changes += 1
            elif result.success:
                summary.statuses_clean += 1
            else:
                summary.statuses_failed += 1
        case GitAction.pull:
            summary.pulls_attempted += 1
            summary.pulls_successful += int(result.success)
            summary.pulls_failed += int(not result.success)
        case GitAction.commit:
            summary.commits_attempted += 1
            if result.success and result.had_changes:
                summary.commits_successful += 1
            elif result.success:
                summary.commits_no_changes += 1
            else:
                summary.commits_failed += 1
        case GitAction.push:
            summary.pushes_attempted += 1
            summary.pushes_successful += int(result.success)
            summary.pushes_failed += int(not result.success)
        case _ as unreachable:
            assert_never(unreachable)
    if not result.success:
        summary.failed_operations.append(result)


def perform_git_operations(repos_root: Path, status: bool, pull: bool, commit: bool, push: bool, recursive: bool, auto_uv_sync: bool) -> None:
    print(f"\n🔄 Performing Git actions on repositories @ `{repos_root}`...")
    requested_actions = tuple(
        action
        for enabled, action in ((status, GitAction.status), (pull, GitAction.pull), (commit, GitAction.commit), (push, GitAction.push))
        if enabled
    )
    paths = _repository_candidates(repos_root=repos_root, recursive=recursive)
    summary = GitOperationSummary()
    max_workers = min(32, (os.cpu_count() or 1) * 5, len(paths) or 1)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_process_repository_path, path, requested_actions, auto_uv_sync): path for path in paths}
        for future in concurrent.futures.as_completed(futures):
            payload = future.result()
            summary.total_paths_processed += 1
            if not payload["is_git"]:
                summary.non_git_paths += 1
                continue
            summary.git_repos_found += 1
            if payload["repo_remotes_count"] == 0:
                summary.repos_without_remotes.append(payload["path"])
            for result in payload["results"]:
                _record_result(summary=summary, result=result)
    print_git_operations_summary(summary=summary, operations_performed=list(requested_actions))
