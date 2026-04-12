from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import cast

import git.repo
import pytest

from machineconfig.scripts.python.helpers.helpers_repos import record as record_module
from machineconfig.utils.schemas.repos.repos_types import GitVersionInfo, RepoRecordDict, RepoRemote


class FailingCommit:
    @property
    def hexsha(self) -> str:
        raise ValueError("missing commit")


class DetachedReference:
    @property
    def name(self) -> str:
        raise TypeError("detached")


class FakeHead:
    def __init__(self) -> None:
        self.commit = FailingCommit()
        self.reference = DetachedReference()


class FakeRepo:
    def __init__(self, working_dir: Path, remotes: list[RepoRemote], dirty: bool) -> None:
        self.working_dir = str(working_dir)
        self.remotes = [SimpleNamespace(name=remote["name"], url=remote["url"]) for remote in remotes]
        self.head = FakeHead()
        self._dirty = dirty

    def is_dirty(self, untracked_files: bool) -> bool:
        _ = untracked_files
        return self._dirty


def _repo_record(parent_dir: Path, name: str, branch: str, remotes: list[RepoRemote], is_dirty: bool) -> RepoRecordDict:
    version: GitVersionInfo = {"branch": branch, "commit": "deadbeef"}
    return {
        "name": name,
        "parentDir": str(parent_dir),
        "currentBranch": branch,
        "remotes": remotes,
        "version": version,
        "isDirty": is_dirty,
    }


def test_build_tree_structure_shows_runtime_status_information(tmp_path: Path) -> None:
    repos_root = tmp_path / "repos"
    repos = [
        _repo_record(repos_root, "alpha", "main", [{"name": "origin", "url": "ssh://origin"}], False),
        _repo_record(repos_root / "group", "beta", "feature", [], True),
        _repo_record(tmp_path / "outside", "gamma", "DETACHED", [{"name": "origin", "url": "ssh://origin"}], False),
    ]

    tree = record_module.build_tree_structure(repos=repos, repos_root=repos_root)

    assert "📂 repos/" in tree
    assert "📦 alpha (main)" in tree
    assert "[✅ CLEAN]" in tree
    assert "DIRTY" in tree
    assert "NO_REMOTE" in tree
    assert "DETACHED" in tree
    assert str((tmp_path / "outside").absolute()) in tree


def test_record_a_repo_handles_unknown_commit_and_detached_head(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    remotes: list[RepoRemote] = [{"name": "backup", "url": "ssh://backup"}]
    fake_repo = FakeRepo(working_dir=repo_path, remotes=remotes, dirty=True)

    monkeypatch.setattr(git.repo, "Repo", lambda path, search_parent_directories: fake_repo)
    monkeypatch.setattr(record_module.PathExtended, "home", classmethod(lambda cls: tmp_path))

    result = record_module.record_a_repo(
        path=cast(object, repo_path),
        search_parent_directories=False,
        preferred_remote="origin",
    )

    assert result["version"]["commit"] == "UNKNOWN"
    assert result["currentBranch"] == "DETACHED"
    assert result["remotes"] == remotes
    assert result["isDirty"]


def test_count_functions_ignore_hidden_directories_and_recurse(tmp_path: Path) -> None:
    repos_root = tmp_path / "repos"
    repos_root.mkdir()
    (repos_root / "project-a" / ".git").mkdir(parents=True)
    (repos_root / "group" / "project-b" / ".git").mkdir(parents=True)
    (repos_root / ".hidden" / "project-c" / ".git").mkdir(parents=True)

    assert record_module.count_git_repositories(str(repos_root), r=True) == 2
    assert record_module.count_total_directories(str(repos_root), r=True) == 3


def test_record_repos_recursively_records_all_visible_git_roots(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repos_root = tmp_path / "repos"
    (repos_root / "project-a" / ".git").mkdir(parents=True)
    (repos_root / "group" / "project-b" / ".git").mkdir(parents=True)
    (repos_root / ".hidden" / "project-c" / ".git").mkdir(parents=True)

    monkeypatch.setattr(
        record_module,
        "record_a_repo",
        lambda path, search_parent_directories, preferred_remote: _repo_record(
            parent_dir=Path(path).parent,
            name=Path(path).name,
            branch="main",
            remotes=[],
            is_dirty=False,
        ),
    )

    result = record_module.record_repos_recursively(
        repos_root=str(repos_root),
        r=True,
        progress=None,
        scan_task_id=None,
        process_task_id=None,
    )

    assert [entry["name"] for entry in result] == ["project-a", "project-b"]


def test_resolve_directory_defaults_to_current_working_directory(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)

    resolved = record_module._resolve_directory(directory=None)

    assert resolved == tmp_path.resolve()
