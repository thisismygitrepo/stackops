import json
from pathlib import Path
from typing import cast

import pytest
from git.repo import Repo

from stackops.scripts.python.helpers.helpers_repos.version_capture import VersionOperationError, capture_repository
from stackops.scripts.python.helpers.helpers_repos.version_checkout import checkout_declared_version
from stackops.scripts.python.helpers.helpers_repos.version_constants import CHECKOUT_BACKUP_REF_PREFIX
from stackops.scripts.python.helpers.helpers_repos.version_models import DeclaredVersion, RepositorySnapshot, VersionsFile
from stackops.scripts.python.helpers.helpers_repos.version_store import (
    VersionStoreError,
    append_declared_version,
    empty_versions_file,
    load_versions_file,
    save_versions_file,
)


def _initialize_repository(repository_path: Path, content: str) -> Repo:
    repository = Repo.init(repository_path, initial_branch="main")
    with repository.config_writer() as config:
        config.set_value("user", "name", "Stackops Tests")
        config.set_value("user", "email", "stackops-tests@example.invalid")
    tracked_file = repository_path.joinpath("tracked.txt")
    tracked_file.write_text(content, encoding="utf-8")
    repository.index.add([tracked_file.as_posix()])
    repository.index.commit("initial")
    return repository


def _commit_tracked_change(repository: Repo, repository_path: Path, content: str, message: str) -> str:
    tracked_file = repository_path.joinpath("tracked.txt")
    tracked_file.write_text(content, encoding="utf-8")
    repository.index.add([tracked_file.as_posix()])
    return cast(str, repository.index.commit(message).hexsha).lower()


def _declared_version(version: str, snapshot: RepositorySnapshot) -> DeclaredVersion:
    return {"version": version, "message": f"Captured {version}", "repositories": [snapshot]}


def _backup_refs(repository: Repo) -> list[str]:
    output = cast(str, repository.git.for_each_ref("--format=%(refname)", CHECKOUT_BACKUP_REF_PREFIX))
    return output.splitlines()


def test_capture_reads_authoritative_branches_from_local_bare_remote(tmp_path: Path) -> None:
    remote_path = tmp_path.joinpath("remote.git")
    Repo.init(remote_path, bare=True, initial_branch="main")
    workspace = tmp_path.joinpath("workspace")
    repository_path = workspace.joinpath("application")
    repository = _initialize_repository(repository_path=repository_path, content="initial\n")
    initial_commit = cast(str, repository.head.commit.hexsha).lower()
    origin = repository.create_remote("origin", remote_path.as_posix())
    origin.push("main:main").raise_if_error()

    publisher_path = tmp_path.joinpath("publisher")
    publisher = Repo.clone_from(remote_path.as_posix(), publisher_path, branch="main")
    with publisher.config_writer() as config:
        config.set_value("user", "name", "Stackops Tests")
        config.set_value("user", "email", "stackops-tests@example.invalid")
    advertised_commit = _commit_tracked_change(repository=publisher, repository_path=publisher_path, content="published\n", message="published")
    publisher.remote("origin").push("main:main").raise_if_error()
    repository.git.update_ref("refs/remotes/origin/main", initial_commit)

    snapshot = capture_repository(repos_root=workspace, repository_path=repository_path)

    assert cast(str, repository.commit("refs/remotes/origin/main").hexsha).lower() == initial_commit
    assert snapshot["commit"] == initial_commit
    assert snapshot["remotes"] == [{"name": "origin", "urls": [remote_path.as_posix()], "branches": [{"name": "main", "commit": advertised_commit}]}]


def test_versions_file_append_round_trip_and_duplicate_rejection(tmp_path: Path) -> None:
    workspace = tmp_path.joinpath("workspace")
    repository_path = workspace.joinpath("application")
    _initialize_repository(repository_path=repository_path, content="initial\n")
    snapshot = capture_repository(repos_root=workspace, repository_path=repository_path)
    declared_version = _declared_version(version="release-1", snapshot=snapshot)
    versions_file = append_declared_version(versions_file=empty_versions_file(), declared_version=declared_version)
    versions_path = workspace.joinpath("versions.json")

    save_versions_file(versions_file=versions_file, path=versions_path)

    assert load_versions_file(path=versions_path, allow_missing=False) == versions_file
    with pytest.raises(VersionStoreError, match="already declared"):
        append_declared_version(versions_file=versions_file, declared_version=declared_version)

    duplicate_file: VersionsFile = {"schemaVersion": "1", "versions": [declared_version, declared_version]}
    with pytest.raises(VersionStoreError, match="duplicate version identifiers"):
        save_versions_file(versions_file=duplicate_file, path=versions_path)
    versions_path.write_text(json.dumps(duplicate_file), encoding="utf-8")
    with pytest.raises(VersionStoreError, match="duplicate version identifiers"):
        load_versions_file(path=versions_path, allow_missing=False)


def test_checkout_restores_and_rewinds_attached_branch_with_recovery_ref(tmp_path: Path) -> None:
    workspace = tmp_path.joinpath("workspace")
    repository_path = workspace.joinpath("application")
    repository = _initialize_repository(repository_path=repository_path, content="target\n")
    snapshot = capture_repository(repos_root=workspace, repository_path=repository_path)
    newer_commit = _commit_tracked_change(repository=repository, repository_path=repository_path, content="newer\n", message="newer")
    repository.create_head("scratch", snapshot["commit"])
    repository.git.switch("scratch")

    results = checkout_declared_version(
        repos_root=workspace, declared_version=_declared_version(version="release-1", snapshot=snapshot), dry_run=False
    )

    recovery_refs = results[0]["backupRefs"]
    assert results[0]["changed"]
    assert len(recovery_refs) == 1
    recovery_ref = recovery_refs[0]
    assert repository.active_branch.name == "main"
    assert cast(str, repository.head.commit.hexsha).lower() == snapshot["commit"]
    assert cast(str, repository.commit(recovery_ref).hexsha).lower() == newer_commit
    assert recovery_ref in _backup_refs(repository=repository)


def test_checkout_rejects_dirty_captured_target_before_mutating_repository(tmp_path: Path) -> None:
    workspace = tmp_path.joinpath("workspace")
    repository_path = workspace.joinpath("application")
    repository = _initialize_repository(repository_path=repository_path, content="target\n")
    snapshot = capture_repository(repos_root=workspace, repository_path=repository_path)
    snapshot["isDirty"] = True
    current_commit = _commit_tracked_change(repository=repository, repository_path=repository_path, content="current\n", message="current")

    with pytest.raises(VersionOperationError, match="captured dirty repositories"):
        checkout_declared_version(repos_root=workspace, declared_version=_declared_version(version="dirty-target", snapshot=snapshot), dry_run=False)

    assert cast(str, repository.head.commit.hexsha).lower() == current_commit
    assert _backup_refs(repository=repository) == []


def test_checkout_preflights_every_current_worktree_before_mutating_any_repository(tmp_path: Path) -> None:
    workspace = tmp_path.joinpath("workspace")
    first_path = workspace.joinpath("alpha")
    second_path = workspace.joinpath("bravo")
    first_repository = _initialize_repository(repository_path=first_path, content="alpha target\n")
    second_repository = _initialize_repository(repository_path=second_path, content="bravo target\n")
    first_snapshot = capture_repository(repos_root=workspace, repository_path=first_path)
    second_snapshot = capture_repository(repos_root=workspace, repository_path=second_path)
    first_current_commit = _commit_tracked_change(
        repository=first_repository, repository_path=first_path, content="alpha current\n", message="alpha current"
    )
    second_path.joinpath("untracked.txt").write_text("dirty\n", encoding="utf-8")
    declared_version: DeclaredVersion = {"version": "release-1", "message": "Both repositories", "repositories": [first_snapshot, second_snapshot]}

    with pytest.raises(VersionOperationError, match="Refusing to overwrite dirty repository"):
        checkout_declared_version(repos_root=workspace, declared_version=declared_version, dry_run=False)

    assert cast(str, first_repository.head.commit.hexsha).lower() == first_current_commit
    assert first_repository.active_branch.name == "main"
    assert _backup_refs(repository=first_repository) == []
    assert _backup_refs(repository=second_repository) == []
