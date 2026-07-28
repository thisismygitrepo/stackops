import concurrent.futures
import os
from pathlib import Path
from typing import TypedDict, assert_never

from git.exc import InvalidGitRepositoryError
from git.repo import Repo

from stackops.scripts.python.helpers.helpers_repos.action_helper import (
    GitAction,
    GitOperationResult,
    GitOperationSummary,
    print_git_operations_summary,
)
from stackops.scripts.python.helpers.helpers_repos.discovery import repository_candidates
from stackops.scripts.python.helpers.helpers_repos.git_action import git_action


class RepositoryOperationPayload(TypedDict):
    path: Path
    is_git: bool
    results: list[GitOperationResult]


def _process_repository_path(
    path: Path, actions: tuple[GitAction, ...], commit_message: str | None, auto_uv_sync: bool, dry_run: bool
) -> RepositoryOperationPayload:
    try:
        Repo(path, search_parent_directories=False)
    except InvalidGitRepositoryError:
        return {"path": path, "is_git": False, "results": []}

    results: list[GitOperationResult] = []
    for action in actions:
        result = git_action(path=path, action=action, message=commit_message, auto_uv_sync=auto_uv_sync, dry_run=dry_run)
        results.append(result)
        if not result.success:
            break
    return {"path": path, "is_git": True, "results": results}


def _record_result(summary: GitOperationSummary, result: GitOperationResult) -> None:
    summary.operation_results.append(result)
    match result.action:
        case GitAction.status:
            summary.statuses_attempted += 1
            summary.statuses_clean += int(result.success and not result.had_changes)
            summary.statuses_with_changes += int(result.success and result.had_changes)
            summary.statuses_failed += int(not result.success)
        case GitAction.pull:
            summary.pulls_planned += int(result.dry_run)
            summary.pulls_attempted += int(not result.dry_run)
            summary.pulls_successful += int(result.success and not result.dry_run)
            summary.pulls_failed += int(not result.success)
        case GitAction.commit:
            summary.commits_planned += int(result.dry_run)
            summary.commits_attempted += int(not result.dry_run)
            summary.commits_successful += int(result.success and result.had_changes and not result.dry_run)
            summary.commits_no_changes += int(result.success and not result.had_changes and not result.dry_run)
            summary.commits_failed += int(not result.success)
        case GitAction.push:
            summary.pushes_planned += int(result.dry_run)
            summary.pushes_attempted += int(not result.dry_run)
            summary.pushes_successful += int(result.success and not result.dry_run)
            summary.pushes_failed += int(not result.success)
        case _ as unreachable:
            assert_never(unreachable)
    if not result.success:
        summary.failed_operations.append(result)


def perform_git_operations(
    repos_root: Path,
    status: bool,
    pull: bool,
    commit: bool,
    push: bool,
    recursive: bool,
    auto_uv_sync: bool,
    commit_message: str | None,
    dry_run: bool,
) -> GitOperationSummary:
    print(f"\n🔄 Performing Git actions on repositories @ `{repos_root}`...")
    requested_actions = tuple(
        action
        for enabled, action in ((status, GitAction.status), (pull, GitAction.pull), (commit, GitAction.commit), (push, GitAction.push))
        if enabled
    )
    paths = repository_candidates(repos_root=repos_root, recursive=recursive)
    summary = GitOperationSummary(dry_run=dry_run)
    max_workers = min(32, (os.cpu_count() or 1) * 5, len(paths) or 1)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(_process_repository_path, path, requested_actions, commit_message, auto_uv_sync, dry_run) for path in paths]
        payloads = sorted((future.result() for future in concurrent.futures.as_completed(futures)), key=lambda item: item["path"])

    for payload in payloads:
        summary.total_paths_processed += 1
        if not payload["is_git"]:
            summary.non_git_paths += 1
            continue
        summary.git_repos_found += 1
        for result in payload["results"]:
            _record_result(summary=summary, result=result)
    print_git_operations_summary(summary=summary, operations_performed=requested_actions)
    return summary
