

from dataclasses import dataclass
from pathlib import Path
import sys
from types import ModuleType

import pytest

from stackops.scripts.python.helpers.helpers_repos import action as target
from stackops.scripts.python.helpers.helpers_repos.action_helper import GitAction, GitOperationResult, GitOperationSummary
from stackops.utils.path_extended import PathExtended


@dataclass(slots=True)
class FakeBranch:
    name: str


class FakeGitIndex:
    def __init__(self) -> None:
        self.commit_messages: list[str] = []

    def commit(self, message: str) -> None:
        self.commit_messages.append(message)


class FakeGitCommands:
    def __init__(self) -> None:
        self.add_all_calls = 0

    def add(self, *, A: bool) -> None:
        if A:
            self.add_all_calls += 1


class FakeRemote:
    def __init__(self, name: str, url: str, should_fail: bool) -> None:
        self.name = name
        self.url = url
        self.should_fail = should_fail
        self.pushed_branches: list[str] = []

    def push(self, branch_name: str) -> None:
        self.pushed_branches.append(branch_name)
        if self.should_fail:
            raise RuntimeError(f"{self.name} down")


class FakeRepo:
    def __init__(
        self,
        *,
        dirty: bool,
        untracked_files: list[str],
        remotes: list[FakeRemote],
    ) -> None:
        self._dirty = dirty
        self.untracked_files = untracked_files
        self.remotes = remotes
        self.active_branch = FakeBranch(name="main")
        self.index = FakeGitIndex()
        self.git = FakeGitCommands()

    def is_dirty(self) -> bool:
        return self._dirty


def _install_fake_git_modules(
    monkeypatch: pytest.MonkeyPatch,
    repo_lookup: dict[str, FakeRepo],
) -> type[Exception]:
    class FakeInvalidGitRepositoryError(Exception):
        pass

    def repo_factory(path: str, search_parent_directories: bool = False) -> FakeRepo:
        _ = search_parent_directories
        if path in repo_lookup:
            return repo_lookup[path]
        raise FakeInvalidGitRepositoryError

    git_module = ModuleType("git")
    exc_module = ModuleType("git.exc")
    repo_module = ModuleType("git.repo")
    setattr(exc_module, "InvalidGitRepositoryError", FakeInvalidGitRepositoryError)
    setattr(repo_module, "Repo", repo_factory)
    setattr(git_module, "exc", exc_module)
    setattr(git_module, "repo", repo_module)

    monkeypatch.setitem(sys.modules, "git", git_module)
    monkeypatch.setitem(sys.modules, "git.exc", exc_module)
    monkeypatch.setitem(sys.modules, "git.repo", repo_module)

    return FakeInvalidGitRepositoryError


def test_git_action_commit_reports_clean_repository(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_path = PathExtended(str(tmp_path.joinpath("repo")))
    repo_path.mkdir(parents=True)
    repo = FakeRepo(dirty=False, untracked_files=[], remotes=[FakeRemote(name="origin", url="git@example/repo", should_fail=False)])
    _install_fake_git_modules(monkeypatch=monkeypatch, repo_lookup={str(repo_path): repo})

    result = target.git_action(
        path=repo_path,
        action=GitAction.commit,
        mess=None,
        r=False,
        auto_uv_sync=False,
    )

    assert result.success is True
    assert result.had_changes is False
    assert result.message == "No changes to commit"
    assert repo.git.add_all_calls == 0
    assert repo.index.commit_messages == []


def test_git_action_push_aggregates_remote_failures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_path = PathExtended(str(tmp_path.joinpath("repo")))
    repo_path.mkdir(parents=True)
    repo = FakeRepo(
        dirty=False,
        untracked_files=[],
        remotes=[
            FakeRemote(name="origin", url="git@example/repo", should_fail=False),
            FakeRemote(name="backup", url="git@example/backup", should_fail=True),
        ],
    )
    _install_fake_git_modules(monkeypatch=monkeypatch, repo_lookup={str(repo_path): repo})

    result = target.git_action(
        path=repo_path,
        action=GitAction.push,
        mess=None,
        r=False,
        auto_uv_sync=False,
    )

    assert result.success is False
    assert result.remote_count == 2
    assert "backup" in result.message
    assert repo.remotes[0].pushed_branches == ["main"]
    assert repo.remotes[1].pushed_branches == ["main"]


def test_perform_git_operations_updates_summary_counts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repos_root = PathExtended(str(tmp_path.joinpath("repos")))
    git_repo_path = PathExtended(str(repos_root.joinpath("repo-one")))
    non_git_path = PathExtended(str(repos_root.joinpath("plain-dir")))
    git_repo_path.mkdir(parents=True)
    non_git_path.mkdir()
    repo = FakeRepo(dirty=False, untracked_files=[], remotes=[FakeRemote(name="origin", url="git@example/repo", should_fail=False)])
    _install_fake_git_modules(monkeypatch=monkeypatch, repo_lookup={str(git_repo_path): repo})

    captured: list[tuple[GitOperationSummary, list[str]]] = []

    def fake_git_action(
        *,
        path: PathExtended,
        action: GitAction,
        mess: str | None,
        r: bool,
        auto_uv_sync: bool,
    ) -> GitOperationResult:
        _ = (path, mess, r, auto_uv_sync)
        if action == GitAction.pull:
            return GitOperationResult(repo_path=git_repo_path, action="pull", success=True, message="pulled", remote_count=1)
        return GitOperationResult(
            repo_path=git_repo_path,
            action="commit",
            success=True,
            message="clean",
            had_changes=False,
            remote_count=1,
        )

    def capture_summary(summary: GitOperationSummary, operations: list[str]) -> None:
        captured.append((summary, operations))

    monkeypatch.setattr(target, "git_action", fake_git_action)
    monkeypatch.setattr(target, "print_git_operations_summary", capture_summary)

    target.perform_git_operations(
        repos_root=repos_root,
        pull=True,
        commit=True,
        push=False,
        recursive=False,
        auto_uv_sync=False,
    )

    assert len(captured) == 1
    summary, operations = captured[0]
    assert operations == ["pull", "commit"]
    assert summary.total_paths_processed == 2
    assert summary.git_repos_found == 1
    assert summary.non_git_paths == 1
    assert summary.pulls_attempted == 1
    assert summary.pulls_successful == 1
    assert summary.commits_attempted == 1
    assert summary.commits_no_changes == 1
