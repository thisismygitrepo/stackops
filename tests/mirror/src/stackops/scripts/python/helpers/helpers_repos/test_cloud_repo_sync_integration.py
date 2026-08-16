from dataclasses import dataclass
from io import StringIO
from pathlib import Path

import pytest
from git.repo import Repo
from rich.console import Console

from stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_conflicts import (
    MergeConflict,
    MergeConflictResolutionSide,
    get_merge_conflicts,
    resolve_merge_conflicts,
)
from stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_git import MergeConflictResult, merge_remote_copy
from stackops.scripts.python.helpers.helpers_repos.cloud_repo_sync_integration import (
    create_integration_worktree,
    fast_forward_local_repo,
    remove_integration_worktree,
)


@dataclass(frozen=True)
class RepositoryContents:
    both_modified: bytes
    local_deletes: bytes | None
    remote_deletes: bytes | None


@dataclass(frozen=True)
class DivergedRepositories:
    live_repo: Repo
    live_root: Path
    remote_root: Path


EXPECTED_CONFLICTS: tuple[MergeConflict, ...] = (
    MergeConflict(path="both-modified.txt", local="present", remote="present"),
    MergeConflict(path="local-deletes.txt", local="deleted", remote="present"),
    MergeConflict(path="remote-deletes.txt", local="present", remote="deleted"),
)


def _configure_identity(repo: Repo) -> None:
    with repo.config_writer() as config:
        config.set_value("user", "name", "StackOps Tests")
        config.set_value("user", "email", "stackops-tests@example.invalid")


def _create_diverged_repositories(tmp_path: Path) -> DivergedRepositories:
    live_root = tmp_path.joinpath("live")
    live_repo = Repo.init(live_root, initial_branch="master")
    _configure_identity(repo=live_repo)
    live_root.joinpath("both-modified.txt").write_text("base\n", encoding="utf-8")
    live_root.joinpath("local-deletes.txt").write_text("base\n", encoding="utf-8")
    live_root.joinpath("remote-deletes.txt").write_text("base\n", encoding="utf-8")
    live_repo.index.add(["both-modified.txt", "local-deletes.txt", "remote-deletes.txt"])
    live_repo.index.commit("base")

    remote_root = tmp_path.joinpath("remote")
    remote_repo = Repo.clone_from(live_root.as_posix(), remote_root, branch="master")
    _configure_identity(repo=remote_repo)

    live_root.joinpath("both-modified.txt").write_text("local\n", encoding="utf-8")
    live_root.joinpath("remote-deletes.txt").write_text("local edit\n", encoding="utf-8")
    live_repo.git.rm("--", "local-deletes.txt")
    live_repo.index.add(["both-modified.txt", "remote-deletes.txt"])
    live_repo.index.commit("local divergence")

    remote_root.joinpath("both-modified.txt").write_text("remote\n", encoding="utf-8")
    remote_root.joinpath("local-deletes.txt").write_text("remote edit\n", encoding="utf-8")
    remote_repo.git.rm("--", "remote-deletes.txt")
    remote_repo.index.add(["both-modified.txt", "local-deletes.txt"])
    remote_repo.index.commit("remote divergence")
    remote_repo.close()
    return DivergedRepositories(live_repo=live_repo, live_root=live_root, remote_root=remote_root)


def _read_repository_contents(root: Path) -> RepositoryContents:
    local_deletes_path = root.joinpath("local-deletes.txt")
    remote_deletes_path = root.joinpath("remote-deletes.txt")
    return RepositoryContents(
        both_modified=root.joinpath("both-modified.txt").read_bytes(),
        local_deletes=local_deletes_path.read_bytes() if local_deletes_path.exists() else None,
        remote_deletes=remote_deletes_path.read_bytes() if remote_deletes_path.exists() else None,
    )


def _assert_live_unchanged(repositories: DivergedRepositories, expected_head: str, expected_contents: RepositoryContents) -> None:
    assert str(repositories.live_repo.head.commit.hexsha) == expected_head
    assert _read_repository_contents(root=repositories.live_root) == expected_contents
    assert get_merge_conflicts(repo=repositories.live_repo) == ()
    assert not repositories.live_repo.is_dirty(untracked_files=True)


RESOLUTION_CASES: tuple[tuple[MergeConflictResolutionSide, RepositoryContents], ...] = (
    ("remote", RepositoryContents(both_modified=b"remote\n", local_deletes=b"remote edit\n", remote_deletes=None)),
    ("local", RepositoryContents(both_modified=b"local\n", local_deletes=None, remote_deletes=b"local edit\n")),
)


@pytest.mark.parametrize(("accept_side", "expected_contents"), RESOLUTION_CASES)
def test_isolated_merge_resolves_mixed_conflicts_before_fast_forwarding_live_repo(
    tmp_path: Path, accept_side: MergeConflictResolutionSide, expected_contents: RepositoryContents
) -> None:
    repositories = _create_diverged_repositories(tmp_path=tmp_path)
    live_head = str(repositories.live_repo.head.commit.hexsha)
    live_contents = _read_repository_contents(root=repositories.live_root)
    integration_worktree = create_integration_worktree(repo=repositories.live_repo, worktree_root=tmp_path.joinpath("integration"))
    integration_repo = Repo(integration_worktree.root)
    try:
        merge_result = merge_remote_copy(repo=integration_repo, remote_path=repositories.remote_root, console=Console(file=StringIO()))

        assert isinstance(merge_result, MergeConflictResult)
        assert merge_result.conflicts == EXPECTED_CONFLICTS
        assert tuple(remote.name for remote in repositories.live_repo.remotes) == ()
        _assert_live_unchanged(repositories=repositories, expected_head=live_head, expected_contents=live_contents)

        integration_commit = resolve_merge_conflicts(repo=integration_repo, expected_conflicts=merge_result.conflicts, accept_side=accept_side)

        assert _read_repository_contents(root=integration_worktree.root) == expected_contents
        assert get_merge_conflicts(repo=integration_repo) == ()
        assert not integration_repo.is_dirty(untracked_files=True)
        _assert_live_unchanged(repositories=repositories, expected_head=live_head, expected_contents=live_contents)

        updated_head = fast_forward_local_repo(
            local_repo=repositories.live_repo, integration_repo=integration_repo, expected_local_head=integration_worktree.base_commit
        )

        assert updated_head == integration_commit
        assert str(repositories.live_repo.head.commit.hexsha) == integration_commit
        assert _read_repository_contents(root=repositories.live_root) == expected_contents
        assert not repositories.live_repo.is_dirty(untracked_files=True)
        assert tuple(remote.name for remote in repositories.live_repo.remotes) == ()
    finally:
        integration_repo.close()
        remove_integration_worktree(local_repo=repositories.live_repo, integration_worktree=integration_worktree)

    assert not integration_worktree.root.exists()


def test_merge_resolution_rejects_stale_conflict_metadata_without_mutating_live_repo(tmp_path: Path) -> None:
    repositories = _create_diverged_repositories(tmp_path=tmp_path)
    live_head = str(repositories.live_repo.head.commit.hexsha)
    live_contents = _read_repository_contents(root=repositories.live_root)
    integration_worktree = create_integration_worktree(repo=repositories.live_repo, worktree_root=tmp_path.joinpath("integration"))
    integration_repo = Repo(integration_worktree.root)
    try:
        merge_result = merge_remote_copy(repo=integration_repo, remote_path=repositories.remote_root, console=Console(file=StringIO()))
        assert isinstance(merge_result, MergeConflictResult)
        assert merge_result.conflicts == EXPECTED_CONFLICTS
        integration_repo.git.checkout("--ours", "--", "both-modified.txt")
        integration_repo.git.add("--", "both-modified.txt")
        current_conflicts = get_merge_conflicts(repo=integration_repo)
        assert current_conflicts == EXPECTED_CONFLICTS[1:]

        with pytest.raises(RuntimeError, match="Merge conflicts changed after they were presented"):
            resolve_merge_conflicts(repo=integration_repo, expected_conflicts=merge_result.conflicts, accept_side="remote")

        assert get_merge_conflicts(repo=integration_repo) == current_conflicts
        _assert_live_unchanged(repositories=repositories, expected_head=live_head, expected_contents=live_contents)
    finally:
        integration_repo.close()
        remove_integration_worktree(local_repo=repositories.live_repo, integration_worktree=integration_worktree)

    assert not integration_worktree.root.exists()
