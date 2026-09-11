from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_conflicts import ConflictResolutionAction


if TYPE_CHECKING:
    from git.repo import Repo
    from rich.console import Console


@dataclass(frozen=True)
class IntegrationWorktree:
    root: Path
    base_commit: str


def create_integration_worktree(repo: "Repo", worktree_root: Path) -> IntegrationWorktree:
    if worktree_root.exists():
        raise FileExistsError(f"Integration worktree path already exists: {worktree_root}")
    worktree_root.parent.mkdir(parents=True, exist_ok=True)
    base_commit = str(repo.head.commit.hexsha)
    repo.git.worktree("add", "--detach", str(worktree_root), base_commit)
    return IntegrationWorktree(root=worktree_root, base_commit=base_commit)


def fast_forward_local_repo(local_repo: "Repo", integration_repo: "Repo", expected_local_head: str) -> str:
    from stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_conflicts import get_merge_conflicts

    current_local_head = str(local_repo.head.commit.hexsha)
    if current_local_head != expected_local_head:
        raise RuntimeError(f"Local HEAD changed during repository integration: expected {expected_local_head}, found {current_local_head}.")
    if local_repo.is_dirty(untracked_files=True):
        raise RuntimeError("Local repository changed during repository integration.")
    if integration_repo.is_dirty(untracked_files=True):
        raise RuntimeError("Integration worktree must be clean before updating the local repository.")
    if len(get_merge_conflicts(repo=integration_repo)) > 0:
        raise RuntimeError("Integration worktree still contains unresolved merge paths.")

    integration_commit = str(integration_repo.head.commit.hexsha)
    local_repo.git.merge(integration_commit, ff_only=True)
    updated_local_head = str(local_repo.head.commit.hexsha)
    if updated_local_head != integration_commit:
        raise RuntimeError(f"Local repository did not reach integration commit {integration_commit}; found {updated_local_head}.")
    if local_repo.is_dirty(untracked_files=True):
        raise RuntimeError("Local repository became dirty while applying the integration commit.")
    return integration_commit


def remove_integration_worktree(local_repo: "Repo", integration_worktree: IntegrationWorktree) -> None:
    local_repo.git.worktree("remove", "--force", str(integration_worktree.root))
    integration_parent = integration_worktree.root.parent
    if integration_parent.exists() and not any(integration_parent.iterdir()):
        integration_parent.rmdir()


def integrate_remote_repository(
    local_repo: "Repo", repo_remote_root: Path, integration_root: Path, cloud: str, on_conflict: ConflictResolutionAction, console: "Console"
) -> None:
    from git.repo import Repo
    from rich.panel import Panel
    import typer

    from stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_actions import (
        remove_integration_state,
        select_conflict_action,
        validate_integration_transport,
    )
    from stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_conflicts import MergeConflictResolutionSide, resolve_merge_conflicts
    from stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_git import MergeConflictResult, MergeGitError, merge_remote_copy

    repo_local_root = Path(local_repo.working_dir)
    integration_worktree = create_integration_worktree(repo=local_repo, worktree_root=integration_root)
    integration_repo = Repo(integration_worktree.root)
    merge_result = merge_remote_copy(repo=integration_repo, remote_path=repo_remote_root, console=console)

    if isinstance(merge_result, MergeGitError):
        console.print(
            Panel(
                f"Integration failed and was preserved at {integration_root}\nRemote copy: {repo_remote_root}\n\n{merge_result.details}",
                title="Pull Failed",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)

    if isinstance(merge_result, MergeConflictResult):
        conflict_paths = "\n".join(f"• {conflict.path}" for conflict in merge_result.conflicts)
        console.print(
            Panel(
                f"Live repository remains unchanged.\nIsolated merge: {integration_root}\nRemote copy: {repo_remote_root}\n\nConflicting paths:\n{conflict_paths}",
                title="Merge Conflict",
                border_style="red",
            )
        )
        console.print(Panel("🔄 RESOLVE MERGE CONFLICT", border_style="blue"))
        selected_action = select_conflict_action(on_conflict=on_conflict)
        match selected_action:
            case "stop-on-conflict":
                raise typer.Exit(code=1)
            case "inspect":
                from stackops.scripts.python.helpers.helpers_repos.sync import inspect_repos

                inspect_repos(repo_local_root=str(repo_local_root), repo_remote_root=str(integration_root))
                raise typer.Exit(code=1)
            case "merge-accept-remote" | "merge-accept-local":
                accepted_side: MergeConflictResolutionSide = "remote" if selected_action == "merge-accept-remote" else "local"
                resolve_merge_conflicts(repo=integration_repo, expected_conflicts=merge_result.conflicts, accept_side=accepted_side)
            case "ask":
                raise RuntimeError("Interactive conflict action was not resolved.")

    validate_integration_transport(repo_local_root=repo_local_root, integration_root=integration_root, cloud=cloud)
    fast_forward_local_repo(local_repo=local_repo, integration_repo=integration_repo, expected_local_head=integration_worktree.base_commit)
    remove_integration_state(local_repo=local_repo, integration_repo=integration_repo, integration_worktree=integration_worktree)
