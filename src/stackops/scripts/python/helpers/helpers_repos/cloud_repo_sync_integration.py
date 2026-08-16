from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from git.repo import Repo


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
