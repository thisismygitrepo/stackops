import concurrent.futures
import os
from pathlib import Path

from stackops.scripts.python.helpers.helpers_repos.version_capture import capture_repository
from stackops.scripts.python.helpers.helpers_repos.version_models import (
    DeclaredVersion,
    RepositorySnapshot,
    RepositoryVersionStatus,
    VersionRepositoryState,
)
from stackops.scripts.python.helpers.helpers_repos.version_paths import snapshot_repository_path


def _branch_label(branch: str | None) -> str:
    if branch is None:
        return "detached"
    return branch


def _different_detail(snapshot: RepositorySnapshot, current: RepositorySnapshot) -> str:
    differences: list[str] = []
    if snapshot["branch"] != current["branch"]:
        differences.append(f"branch {_branch_label(current['branch'])!r}, expected {_branch_label(snapshot['branch'])!r}")
    if snapshot["commit"] != current["commit"]:
        differences.append(f"commit {current['commit'][:12]}, expected {snapshot['commit'][:12]}")
    if snapshot["remotes"] != current["remotes"]:
        differences.append("advertised remote branches changed")
    return "; ".join(differences)


def _repository_status(repos_root: Path, snapshot: RepositorySnapshot) -> RepositoryVersionStatus:
    repository_path = snapshot_repository_path(repos_root=repos_root, snapshot=snapshot)
    if not repository_path.exists():
        return {"snapshot": snapshot, "state": VersionRepositoryState.missing, "detail": f"Repository not found: {repository_path}"}
    current = capture_repository(repos_root=repos_root, repository_path=repository_path)
    difference_detail = _different_detail(snapshot=snapshot, current=current)
    if snapshot["isDirty"]:
        detail = "Declared with uncommitted content, which cannot be verified from a dirty-state flag"
        if difference_detail:
            detail = f"{detail}; {difference_detail}"
        return {"snapshot": snapshot, "state": VersionRepositoryState.unverifiable, "detail": detail}
    if current["isDirty"]:
        detail = "Current worktree has uncommitted changes"
        if difference_detail:
            detail = f"{detail}; {difference_detail}"
        return {"snapshot": snapshot, "state": VersionRepositoryState.dirty, "detail": detail}
    if difference_detail:
        return {"snapshot": snapshot, "state": VersionRepositoryState.different, "detail": difference_detail}
    return {"snapshot": snapshot, "state": VersionRepositoryState.exact, "detail": "Local and advertised remote state match"}


def inspect_declared_version(repos_root: Path, declared_version: DeclaredVersion) -> list[RepositoryVersionStatus]:
    snapshots = declared_version["repositories"]
    max_workers = min(32, (os.cpu_count() or 1) * 5, len(snapshots) or 1)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(_repository_status, repos_root, snapshot) for snapshot in snapshots]
        statuses = [future.result() for future in concurrent.futures.as_completed(futures)]
    return sorted(statuses, key=lambda status: status["snapshot"]["path"])
