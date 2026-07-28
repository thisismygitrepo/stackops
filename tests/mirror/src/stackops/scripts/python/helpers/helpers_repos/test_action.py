from pathlib import Path
from typing import Never

import pytest
from git.remote import Remote
from git.repo import Repo

from stackops.scripts.python.helpers.helpers_repos.action import perform_git_operations
from stackops.scripts.python.helpers.helpers_repos.action_helper import GitAction
from stackops.scripts.python.helpers.helpers_repos.git_action import git_action


def _initialize_repository(repository_path: Path) -> Repo:
    repository = Repo.init(repository_path)
    with repository.config_writer() as config:
        config.set_value("user", "name", "Stackops Tests")
        config.set_value("user", "email", "stackops-tests@example.invalid")
    tracked_file = repository_path / "tracked.txt"
    tracked_file.write_text("initial\n")
    repository.index.add([tracked_file.as_posix()])
    repository.index.commit("initial")
    return repository


def test_status_reports_clean_and_changed_working_trees(tmp_path: Path) -> None:
    repository_path = tmp_path / "repository"
    _initialize_repository(repository_path)

    clean_result = git_action(path=repository_path, action=GitAction.status, message=None, auto_uv_sync=False, dry_run=False)

    assert clean_result.success
    assert not clean_result.had_changes
    assert clean_result.message.startswith("##")

    (repository_path / "untracked.txt").write_text("changed\n")
    changed_result = git_action(path=repository_path, action=GitAction.status, message=None, auto_uv_sync=False, dry_run=False)

    assert changed_result.success
    assert changed_result.had_changes
    assert "?? untracked.txt" in changed_result.message


def test_commit_dry_run_preserves_staged_changes(tmp_path: Path) -> None:
    repository_path = tmp_path / "repository"
    repository = _initialize_repository(repository_path)
    tracked_file = repository_path / "tracked.txt"
    tracked_file.write_text("changed\n")
    repository.index.add([tracked_file.as_posix()])
    commit_before = repository.head.commit.hexsha

    result = git_action(path=repository_path, action=GitAction.commit, message="update", auto_uv_sync=False, dry_run=True)

    assert result.success
    assert result.dry_run
    assert repository.head.commit.hexsha == commit_before
    assert repository.index.diff("HEAD")


def test_commit_rejects_unstaged_changes(tmp_path: Path) -> None:
    repository_path = tmp_path / "repository"
    repository = _initialize_repository(repository_path)
    (repository_path / "tracked.txt").write_text("changed\n")
    commit_before = repository.head.commit.hexsha

    result = git_action(path=repository_path, action=GitAction.commit, message="update", auto_uv_sync=False, dry_run=False)

    assert not result.success
    assert "No staged changes" in result.message
    assert repository.head.commit.hexsha == commit_before


def test_commit_does_not_stage_untracked_files(tmp_path: Path) -> None:
    repository_path = tmp_path / "repository"
    repository = _initialize_repository(repository_path)
    tracked_file = repository_path / "tracked.txt"
    tracked_file.write_text("changed\n")
    repository.index.add([tracked_file.as_posix()])
    (repository_path / "untracked-secret.txt").write_text("do not commit\n")

    result = git_action(path=repository_path, action=GitAction.commit, message="update", auto_uv_sync=False, dry_run=False)

    assert result.success
    assert repository.head.commit.message == "update"
    assert repository.untracked_files == ["untracked-secret.txt"]


class RejectedPushResults:
    def __len__(self) -> int:
        return 1

    def raise_if_error(self) -> None:
        raise RuntimeError("remote rejected the push")


def test_push_checks_returned_push_results(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repository_path = tmp_path / "repository"
    repository = _initialize_repository(repository_path)
    repository.create_remote("origin", "https://example.invalid/repository.git")

    def rejected_push(_remote: Remote, _refspec: str) -> RejectedPushResults:
        return RejectedPushResults()

    monkeypatch.setattr(Remote, "push", rejected_push)
    result = git_action(path=repository_path, action=GitAction.push, message=None, auto_uv_sync=False, dry_run=False)

    assert not result.success
    assert "remote rejected the push" in result.message


def test_pull_dry_run_does_not_update_repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repository_path = tmp_path / "repository"
    repository = _initialize_repository(repository_path)
    repository.create_remote("origin", "https://example.invalid/repository.git")

    def unexpected_update(*_arguments: object, **_keyword_arguments: object) -> Never:
        raise AssertionError("update_repository must not run during a dry run")

    monkeypatch.setattr("stackops.scripts.python.helpers.helpers_repos.git_action.update_repository", unexpected_update)
    result = git_action(path=repository_path, action=GitAction.pull, message=None, auto_uv_sync=True, dry_run=True)

    assert result.success
    assert result.dry_run
    assert result.message.startswith("Would pull")


def test_push_dry_run_does_not_contact_remote(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repository_path = tmp_path / "repository"
    repository = _initialize_repository(repository_path)
    repository.create_remote("origin", "https://example.invalid/repository.git")

    def unexpected_push(_remote: Remote, _refspec: str) -> Never:
        raise AssertionError("Remote.push must not run during a dry run")

    monkeypatch.setattr(Remote, "push", unexpected_push)
    result = git_action(path=repository_path, action=GitAction.push, message=None, auto_uv_sync=False, dry_run=True)

    assert result.success
    assert result.dry_run
    assert result.message.startswith("Would push")


def test_parallel_status_results_are_sorted_and_rendered_once(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    parent_path = tmp_path / "repositories"
    _initialize_repository(parent_path / "bravo")
    _initialize_repository(parent_path / "alpha")

    summary = perform_git_operations(
        repos_root=parent_path,
        status=True,
        pull=False,
        commit=False,
        push=False,
        recursive=False,
        auto_uv_sync=False,
        commit_message=None,
        dry_run=False,
    )

    assert [result.repo_path.name for result in summary.operation_results] == ["alpha", "bravo"]
    assert capsys.readouterr().out.count("##") == 2
