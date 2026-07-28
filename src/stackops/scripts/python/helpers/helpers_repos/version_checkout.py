import time
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from git.exc import GitCommandError, InvalidGitRepositoryError, NoSuchPathError
from git.remote import Remote
from git.repo import Repo

from stackops.scripts.python.helpers.helpers_repos.version_capture import VersionOperationError
from stackops.scripts.python.helpers.helpers_repos.version_constants import CHECKOUT_BACKUP_REF_PREFIX, IN_PROGRESS_GIT_MARKERS
from stackops.scripts.python.helpers.helpers_repos.version_models import DeclaredVersion, RemoteSnapshot, RepositoryCheckoutResult, RepositorySnapshot
from stackops.scripts.python.helpers.helpers_repos.version_paths import snapshot_repository_path


@dataclass(frozen=True, slots=True)
class _CheckoutPlan:
    snapshot: RepositorySnapshot
    path: Path
    repository: Repo
    needs_fetch: bool
    requires_checkout: bool
    recovery_points: tuple[tuple[str, str], ...]


def _git_operation_in_progress(repository: Repo) -> str | None:
    git_directory = Path(repository.git_dir).absolute().resolve()
    for marker in IN_PROGRESS_GIT_MARKERS:
        if git_directory.joinpath(marker).exists():
            return marker
    return None


def _commit_exists(repository: Repo, commit: str) -> bool:
    try:
        repository.git.cat_file("-e", f"{commit}^{{commit}}")
    except GitCommandError:
        return False
    return True


def _current_remote(repository: Repo, snapshot: RemoteSnapshot, repository_path: Path) -> Remote:
    matching_remotes = [remote for remote in repository.remotes if remote.name == snapshot["name"]]
    if len(matching_remotes) != 1:
        raise VersionOperationError(f"Remote {snapshot['name']!r} is missing from {repository_path}")
    remote = matching_remotes[0]
    current_urls = sorted({str(url) for url in remote.urls})
    if current_urls != snapshot["urls"]:
        raise VersionOperationError(f"Remote {snapshot['name']!r} URLs changed in {repository_path}: {current_urls!r}, expected {snapshot['urls']!r}")
    return remote


def _fetch_missing_commit(plan: _CheckoutPlan) -> None:
    if not plan.snapshot["remotes"]:
        raise VersionOperationError(f"Commit {plan.snapshot['commit']} is unavailable in local-only repository {plan.path}")
    for remote_snapshot in plan.snapshot["remotes"]:
        remote = _current_remote(repository=plan.repository, snapshot=remote_snapshot, repository_path=plan.path)
        try:
            with plan.repository.git.custom_environment(GIT_TERMINAL_PROMPT="0"):
                remote.fetch()
        except GitCommandError as error:
            raise VersionOperationError(f"Failed to fetch remote {remote.name!r} for {plan.path}: {error}") from error
    if not _commit_exists(repository=plan.repository, commit=plan.snapshot["commit"]):
        raise VersionOperationError(f"Commit {plan.snapshot['commit']} is unavailable after fetching remotes for {plan.path}")


def _branch_in_other_worktree(repository: Repo, branch: str, repository_path: Path) -> Path | None:
    output = cast(str, repository.git.worktree("list", "--porcelain"))
    worktree_path: Path | None = None
    for line in output.splitlines():
        if line.startswith("worktree "):
            worktree_path = Path(line.removeprefix("worktree ")).absolute().resolve()
            continue
        if line == f"branch refs/heads/{branch}" and worktree_path is not None and worktree_path != repository_path:
            return worktree_path
    return None


def _local_branch_commit(repository: Repo, branch: str) -> str | None:
    matching_heads = [head for head in repository.heads if head.name == branch]
    if not matching_heads:
        return None
    return matching_heads[0].commit.hexsha.lower()


def _preflight_repository(repos_root: Path, snapshot: RepositorySnapshot) -> _CheckoutPlan:
    path = snapshot_repository_path(repos_root=repos_root, snapshot=snapshot)
    if not path.exists():
        raise VersionOperationError(f"Repository not found: {path}")
    try:
        repository = Repo(path, search_parent_directories=False)
    except (InvalidGitRepositoryError, NoSuchPathError) as error:
        raise VersionOperationError(f"Not a Git repository: {path}") from error
    if repository.bare or repository.working_tree_dir is None:
        raise VersionOperationError(f"Bare repositories cannot be checked out: {path}")
    try:
        current_commit = repository.head.commit.hexsha.lower()
    except ValueError as error:
        raise VersionOperationError(f"Repository has no commits: {path}") from error
    if repository.is_dirty(untracked_files=True, submodules=True):
        raise VersionOperationError(f"Refusing to overwrite dirty repository: {path}")
    operation_marker = _git_operation_in_progress(repository=repository)
    if operation_marker is not None:
        raise VersionOperationError(f"Git operation {operation_marker} is in progress in {path}")
    branch = snapshot["branch"]
    if branch is not None:
        try:
            repository.git.check_ref_format("--branch", branch)
        except GitCommandError as error:
            raise VersionOperationError(f"Captured branch {branch!r} is invalid for {path}") from error
        other_worktree = _branch_in_other_worktree(repository=repository, branch=branch, repository_path=path)
        if other_worktree is not None:
            raise VersionOperationError(f"Branch {branch!r} is checked out in another worktree: {other_worktree}")
    current_branch = None if repository.head.is_detached else repository.active_branch.name
    recovery_points: list[tuple[str, str]] = []
    if branch is not None:
        branch_commit = _local_branch_commit(repository=repository, branch=branch)
        if branch_commit is not None and branch_commit != snapshot["commit"]:
            recovery_points.append(("target-branch", branch_commit))
    recovery_commits = {commit for _label, commit in recovery_points}
    if current_branch is None and current_commit != snapshot["commit"] and current_commit not in recovery_commits:
        recovery_points.append(("detached-head", current_commit))
    return _CheckoutPlan(
        snapshot=snapshot,
        path=path,
        repository=repository,
        needs_fetch=not _commit_exists(repository=repository, commit=snapshot["commit"]),
        requires_checkout=current_branch != snapshot["branch"] or current_commit != snapshot["commit"],
        recovery_points=tuple(recovery_points),
    )


def _checkout_repository(plan: _CheckoutPlan) -> None:
    branch = plan.snapshot["branch"]
    commit = plan.snapshot["commit"]
    if branch is None:
        plan.repository.git.switch("--detach", commit)
        return
    plan.repository.git.switch("--force-create", branch, commit)


def checkout_declared_version(repos_root: Path, declared_version: DeclaredVersion, dry_run: bool) -> list[RepositoryCheckoutResult]:
    dirty_snapshots = [snapshot["path"] for snapshot in declared_version["repositories"] if snapshot["isDirty"]]
    if dirty_snapshots:
        raise VersionOperationError(
            f"Version {declared_version['version']!r} cannot be restored because it captured dirty repositories: {', '.join(dirty_snapshots)}"
        )
    plans = [_preflight_repository(repos_root=repos_root, snapshot=snapshot) for snapshot in declared_version["repositories"]]
    if not dry_run:
        for plan in plans:
            if plan.needs_fetch:
                _fetch_missing_commit(plan=plan)

    operation_id = str(time.time_ns())
    backup_ref = f"{CHECKOUT_BACKUP_REF_PREFIX}/{operation_id}"
    backup_refs: dict[str, list[str]] = {}
    if not dry_run:
        for plan in plans:
            plan_backup_refs: list[str] = []
            for label, recovery_commit in plan.recovery_points:
                recovery_ref = f"{backup_ref}/{label}"
                try:
                    plan.repository.git.update_ref("-m", "stackops version checkout backup", recovery_ref, recovery_commit)
                except GitCommandError as error:
                    raise VersionOperationError(f"Failed to create recovery ref for {plan.path}: {error}") from error
                plan_backup_refs.append(recovery_ref)
            backup_refs[plan.path.as_posix()] = plan_backup_refs
        for plan in plans:
            if plan.requires_checkout:
                try:
                    _checkout_repository(plan=plan)
                except GitCommandError as error:
                    recovery_refs = ", ".join(backup_refs[plan.path.as_posix()]) or "no refs required"
                    raise VersionOperationError(f"Checkout failed for {plan.path}: {error}. Recovery refs: {recovery_refs}") from error

    return [
        {
            "path": plan.snapshot["path"],
            "branch": plan.snapshot["branch"],
            "commit": plan.snapshot["commit"],
            "changed": plan.requires_checkout,
            "needsFetch": plan.needs_fetch,
            "backupRefs": backup_refs.get(plan.path.as_posix(), []),
        }
        for plan in plans
    ]
