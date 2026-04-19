

from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

import pytest

from stackops.scripts.python.helpers.helpers_repos import clone as clone_module
from stackops.utils.schemas.repos.repos_types import GitVersionInfo, RepoRecordDict, RepoRemote


@dataclass
class FakeGitCommands:
    checked_out_targets: list[str] = field(default_factory=list)

    def checkout(self, target: str) -> None:
        self.checked_out_targets.append(target)


@dataclass
class FakeCommit:
    hexsha: str


@dataclass
class FakeHead:
    commit: FakeCommit
    is_detached: bool


@dataclass
class FakeBranch:
    name: str


@dataclass
class FakeRepo:
    head: FakeHead
    active_branch: FakeBranch
    git: FakeGitCommands


class FakeGitRepoFactory:
    def __init__(self, existing_repo: FakeRepo, cloned_repo: FakeRepo) -> None:
        self.existing_repo = existing_repo
        self.cloned_repo = cloned_repo
        self.opened_paths: list[str] = []
        self.clone_calls: list[tuple[str, str]] = []

    def __call__(self, path: str) -> FakeRepo:
        self.opened_paths.append(path)
        return self.existing_repo

    def clone_from(self, url: str, to_path: str) -> FakeRepo:
        self.clone_calls.append((url, to_path))
        return self.cloned_repo


def _repo_spec(parent_dir: Path, remotes: list[RepoRemote]) -> RepoRecordDict:
    version: GitVersionInfo = {"branch": "feature", "commit": "deadbeefcafebabe"}
    return {
        "name": "demo",
        "parentDir": str(parent_dir),
        "currentBranch": "feature",
        "remotes": remotes,
        "version": version,
        "isDirty": False,
    }


def test_choose_remote_prefers_requested_origin_then_first() -> None:
    remotes: list[RepoRemote] = [
        {"name": "backup", "url": "ssh://backup"},
        {"name": "origin", "url": "ssh://origin"},
    ]

    assert clone_module.choose_remote(remotes=remotes, preferred_remote="backup") == remotes[0]
    assert clone_module.choose_remote(remotes=remotes, preferred_remote=None) == remotes[1]
    assert clone_module.choose_remote(remotes=remotes[:1], preferred_remote="missing") == remotes[0]
    assert clone_module.choose_remote(remotes=[], preferred_remote=None) is None


def test_ensure_destination_creates_parent_directory(tmp_path: Path) -> None:
    destination = clone_module.ensure_destination(parent_dir=str(tmp_path / "nested" / "repos"), name="demo")

    assert destination == tmp_path / "nested" / "repos" / "demo"
    assert destination.parent.is_dir()


def test_checkout_branch_and_commit_only_when_target_changes() -> None:
    repo = FakeRepo(
        head=FakeHead(commit=FakeCommit("deadbeef"), is_detached=False),
        active_branch=FakeBranch("main"),
        git=FakeGitCommands(),
    )

    assert not clone_module.checkout_branch(repo=cast(object, repo), branch="main")
    assert clone_module.checkout_branch(repo=cast(object, repo), branch="feature")
    assert repo.git.checked_out_targets == ["feature"]

    assert not clone_module.checkout_commit(repo=cast(object, repo), commit="deadbeef")
    assert clone_module.checkout_commit(repo=cast(object, repo), commit="cafebabe")
    assert repo.git.checked_out_targets == ["feature", "cafebabe"]


def test_clone_single_repo_reuses_existing_git_repository(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    spec = _repo_spec(parent_dir=tmp_path, remotes=[{"name": "origin", "url": "ssh://origin"}])
    destination = tmp_path / "demo"
    destination.joinpath(".git").mkdir(parents=True)

    repo = FakeRepo(
        head=FakeHead(commit=FakeCommit("deadbeef"), is_detached=False),
        active_branch=FakeBranch("main"),
        git=FakeGitCommands(),
    )
    factory = FakeGitRepoFactory(existing_repo=repo, cloned_repo=repo)
    monkeypatch.setattr(clone_module, "GitRepo", factory)

    status, message = clone_module.clone_single_repo(
        repo_spec=spec,
        preferred_remote=None,
        checkout_branch_flag=False,
        checkout_commit_flag=False,
    )

    assert status == "skipped"
    assert "existing repository reused" in message
    assert factory.opened_paths == [str(destination)]


def test_clone_single_repo_clones_and_reports_checkout(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    spec = _repo_spec(parent_dir=tmp_path, remotes=[{"name": "origin", "url": "ssh://origin"}])
    repo = FakeRepo(
        head=FakeHead(commit=FakeCommit("deadbeef"), is_detached=False),
        active_branch=FakeBranch("main"),
        git=FakeGitCommands(),
    )
    factory = FakeGitRepoFactory(existing_repo=repo, cloned_repo=repo)
    monkeypatch.setattr(clone_module, "GitRepo", factory)
    monkeypatch.setattr(clone_module, "checkout_branch", lambda repo, branch: True)
    monkeypatch.setattr(clone_module, "checkout_commit", lambda repo, commit: True)
    monkeypatch.setattr(clone_module, "pprint", lambda _message: None)

    status, message = clone_module.clone_single_repo(
        repo_spec=spec,
        preferred_remote=None,
        checkout_branch_flag=True,
        checkout_commit_flag=True,
    )

    assert status == "cloned"
    assert factory.clone_calls == [("ssh://origin", str(tmp_path / "demo"))]
    assert "Checked out branch feature & commit deadbeef" in message


def test_clone_single_repo_fails_when_destination_exists_without_git(tmp_path: Path) -> None:
    spec = _repo_spec(parent_dir=tmp_path, remotes=[{"name": "origin", "url": "ssh://origin"}])
    (tmp_path / "demo").mkdir()

    status, message = clone_module.clone_single_repo(
        repo_spec=spec,
        preferred_remote=None,
        checkout_branch_flag=False,
        checkout_commit_flag=False,
    )

    assert status == "failed"
    assert "Destination exists but is not a git repository" in message
