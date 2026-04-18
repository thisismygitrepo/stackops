from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import Future
from pathlib import Path
from types import TracebackType

import pytest

from stackops.scripts.python.helpers.helpers_devops import devops_update_repos as module_under_test
from stackops.scripts.python.helpers.helpers_repos.update import RepositoryUpdateResult


def make_result(repo_path: str, *, status: str, dependencies_changed: bool, uv_sync_ran: bool) -> RepositoryUpdateResult:
    return {
        "repo_path": repo_path,
        "status": status,
        "had_uncommitted_changes": False,
        "uncommitted_files": [],
        "commit_before": "before",
        "commit_after": "after",
        "commits_changed": status == "success",
        "pyproject_changed": dependencies_changed,
        "dependencies_changed": dependencies_changed,
        "uv_sync_ran": uv_sync_ran,
        "uv_sync_success": uv_sync_ran,
        "remotes_processed": [],
        "remotes_skipped": [],
        "error_message": None,
        "is_stackops_repo": False,
        "permissions_updated": False,
    }


class FakeGitRepo:
    def __init__(self, working_dir: str) -> None:
        self.working_dir = working_dir


RepoWorker = Callable[[Path, bool], tuple[RepositoryUpdateResult, Path | None]]


class FakeThreadPoolExecutor:
    def __init__(self, *, max_workers: int) -> None:
        self.max_workers = max_workers

    def __enter__(self) -> FakeThreadPoolExecutor:
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, traceback: TracebackType | None) -> None:
        _ = exc_type
        _ = exc
        _ = traceback

    def submit(self, fn: RepoWorker, expanded_path: Path, allow_password_prompt: bool) -> Future[tuple[RepositoryUpdateResult, Path | None]]:
        future: Future[tuple[RepositoryUpdateResult, Path | None]] = Future()
        future.set_result(fn(expanded_path, allow_password_prompt))
        return future


def fake_as_completed(
    futures: dict[Future[tuple[RepositoryUpdateResult, Path | None]], Path],
) -> list[Future[tuple[RepositoryUpdateResult, Path | None]]]:
    return list(futures)


def test_process_single_repo_returns_repo_path_when_dependency_sync_is_pending(monkeypatch: pytest.MonkeyPatch) -> None:
    repo_path = Path("/tmp/repo-alpha")

    def fake_update_repository(_repo: FakeGitRepo, *, allow_password_prompt: bool, auto_uv_sync: bool) -> RepositoryUpdateResult:
        assert allow_password_prompt is True
        assert auto_uv_sync is True
        return make_result(str(repo_path), status="success", dependencies_changed=True, uv_sync_ran=False)

    monkeypatch.setattr(module_under_test.git, "Repo", lambda *_args, **_kwargs: FakeGitRepo(working_dir=str(repo_path)))
    monkeypatch.setattr(module_under_test, "update_repository", fake_update_repository)

    result, repo_with_changes = module_under_test._process_single_repo(expanded_path=repo_path, allow_password_prompt=True)

    assert result["repo_path"] == str(repo_path)
    assert repo_with_changes == repo_path


def test_process_single_repo_returns_error_result_when_repo_lookup_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    printed: list[object] = []

    def fake_repo(*_args: object, **_kwargs: object) -> FakeGitRepo:
        raise RuntimeError("boom")

    monkeypatch.setattr(module_under_test.git, "Repo", fake_repo)
    monkeypatch.setattr(module_under_test.console, "print", printed.append)

    result, repo_with_changes = module_under_test._process_single_repo(expanded_path=Path("/tmp/repo-beta"), allow_password_prompt=False)

    assert result["status"] == "error"
    assert result["repo_path"] == "/tmp/repo-beta"
    assert result["error_message"] == "boom"
    assert repo_with_changes is None
    assert len(printed) == 1


def test_update_repos_runs_uv_sync_only_for_repositories_that_need_it(monkeypatch: pytest.MonkeyPatch) -> None:
    repo_alpha = Path("/tmp/repo-alpha")
    repo_beta = Path("/tmp/repo-beta")
    alpha_result = make_result(str(repo_alpha), status="success", dependencies_changed=True, uv_sync_ran=False)
    beta_result = make_result(str(repo_beta), status="success", dependencies_changed=False, uv_sync_ran=True)
    results_by_repo: dict[Path, tuple[RepositoryUpdateResult, Path | None]] = {repo_alpha: (alpha_result, repo_alpha), repo_beta: (beta_result, None)}
    uv_sync_calls: list[Path] = []
    displayed_results: list[list[RepositoryUpdateResult]] = []

    def fake_process_single_repo(expanded_path: Path, allow_password_prompt: bool) -> tuple[RepositoryUpdateResult, Path | None]:
        assert allow_password_prompt is False
        return results_by_repo[expanded_path]

    def fake_run_uv_sync(repo_path: Path) -> bool:
        uv_sync_calls.append(repo_path)
        return True

    def fake_display_summary(results: list[RepositoryUpdateResult]) -> None:
        displayed_results.append(results)

    monkeypatch.setattr(module_under_test, "ThreadPoolExecutor", FakeThreadPoolExecutor)
    monkeypatch.setattr(module_under_test, "as_completed", fake_as_completed)
    monkeypatch.setattr(module_under_test, "_process_single_repo", fake_process_single_repo)
    monkeypatch.setattr(module_under_test, "run_uv_sync", fake_run_uv_sync)
    monkeypatch.setattr(module_under_test, "_display_summary", fake_display_summary)

    module_under_test.update_repos(repos=[repo_alpha, repo_beta], allow_password_prompt=False)

    assert uv_sync_calls == [repo_alpha]
    assert displayed_results == [[alpha_result, beta_result]]


def test_main_reads_unique_repository_paths_and_trims_trailing_separator(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_calls: list[tuple[list[Path], bool]] = []

    monkeypatch.setattr(module_under_test, "read_ini", lambda _path: {"general": {"repos": "/tmp/repo-a,/tmp/repo-b,/tmp/repo-a,"}})
    monkeypatch.setattr(module_under_test, "update_repos", lambda repos, allow_password_prompt: captured_calls.append((repos, allow_password_prompt)))

    module_under_test.main(verbose=False, allow_password_prompt=True)

    assert captured_calls == [([Path("/tmp/repo-a"), Path("/tmp/repo-b")], True)]
