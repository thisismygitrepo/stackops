import json
from io import StringIO
from pathlib import Path

import pytest
from git import Actor
from git.repo import Repo
from rich.console import Console
from typer.testing import CliRunner

from stackops.scripts.python.helpers.helpers_devops import cli_self, devops_status_data, devops_status_repos
from stackops.scripts.python.helpers.helpers_devops.cli_repos import get_app
from stackops.scripts.python.helpers.helpers_repos import spec_store
from stackops.scripts.python.helpers.helpers_repos.local_status import inspect_local_repository
from stackops.utils.schemas.repos.repos_types import RepoRecordFile


@pytest.fixture(autouse=True)
def isolated_git_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "gitconfig"))


def _initialize_repository(path: Path) -> Repo:
    repository = Repo.init(path, initial_branch="main")
    tracked_file = path / "tracked.txt"
    tracked_file.write_text("initial\n", encoding="utf-8")
    repository.index.add(["tracked.txt"])
    author = Actor("StackOps Tests", "tests@example.invalid")
    repository.index.commit("initial", author=author, committer=author)
    return repository


def _write_spec(path: Path, repositories: list[Path]) -> None:
    spec: RepoRecordFile = {
        "version": "0.2",
        "repos": [
            {
                "name": repository.name,
                "parentDir": str(repository.parent),
                "currentBranch": "stale-branch",
                "version": {"branch": "stale-branch", "commit": "stale-commit"},
                "remotes": [],
                "isDirty": False,
                "sync": {"mode": "guard", "cloud": "test-cloud", "remotePath": "repos", "ignoreGitignore": False}
                if repository.name == "guarded" else {"mode": "git"},
            }
            for repository in repositories
        ],
    }
    path.write_text(json.dumps(spec), encoding="utf-8")


def test_status_and_list_share_registered_repositories_and_live_changes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COLUMNS", "300")
    clean_path = tmp_path / "clean"
    guarded_path = tmp_path / "guarded"
    invalid_path = tmp_path / "invalid"
    missing_path = tmp_path / "missing"
    with _initialize_repository(clean_path), _initialize_repository(guarded_path):
        (guarded_path / "tracked.txt").write_text("changed\n", encoding="utf-8")
        (guarded_path / "new.txt").write_text("new\n", encoding="utf-8")
        invalid_path.mkdir()
        spec_path = tmp_path / "repos.json"
        _write_spec(spec_path, [missing_path, guarded_path, invalid_path, clean_path])
        monkeypatch.setattr(spec_store, "DEFAULT_REPOS_SPEC_PATH", spec_path)

        status = devops_status_repos.check_repos_status()
        snapshot = devops_status_data.collect_status_section("repos")
        listed = CliRunner().invoke(get_app(), ["list"])
        reported = CliRunner().invoke(cli_self.get_app(), ["status", "--repos", "--plain"])

    assert status.spec_path == spec_path
    assert [repository.name for repository in status.repositories] == ["clean", "guarded", "invalid", "missing"]
    assert [repository.local.state for repository in status.repositories] == ["Clean", "Changed", "Not a Git repo", "Missing"]
    assert status.repositories[1].local.changes == "1m/1n"
    assert status.repositories[1].local.branch == "main"
    assert snapshot.summary == "4 repositories · 3 need attention"
    assert snapshot.level == "attention"
    output = StringIO()
    Console(file=output, width=160, color_system=None).print(snapshot.content)
    rendered = output.getvalue()
    assert str(spec_path) in rendered
    assert listed.exit_code == 0, listed.output
    assert reported.exit_code == 0, reported.output
    for expected in ("clean", "guarded", "invalid", "missing", "1m/1n", "Encrypted guard", "test-cloud"):
        assert expected in rendered
        assert expected in listed.output
        assert expected in reported.output
    assert "config.json" not in rendered
    assert "No repositories configured" not in rendered
    assert "No repositories configured" not in reported.output


def test_clean_registered_repository_is_ready(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "clean"
    with _initialize_repository(path):
        spec_path = tmp_path / "repos.json"
        _write_spec(spec_path, [path])
        monkeypatch.setattr(spec_store, "DEFAULT_REPOS_SPEC_PATH", spec_path)
        snapshot = devops_status_data.collect_status_section("repos")

    assert snapshot.level == "ready"
    assert snapshot.summary == "1 repository · 0 need attention"


def test_empty_registration_is_distinct_from_missing_specification(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    spec_path = tmp_path / "repos.json"
    _write_spec(spec_path, [])
    monkeypatch.setattr(spec_store, "DEFAULT_REPOS_SPEC_PATH", spec_path)
    empty = devops_status_data.collect_status_section("repos")
    assert empty.level == "attention"
    assert empty.summary == "No repositories registered"

    spec_path.unlink()
    missing = devops_status_data.collect_status_section("repos")
    assert missing.level == "error"
    assert missing.summary == "Check failed"
    output = StringIO()
    Console(file=output, width=200, color_system=None).print(missing.content)
    assert f"""Repository specification file not found: {spec_path}""" in output.getvalue()


def test_invalid_specification_reports_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    spec_path = tmp_path / "repos.json"
    spec_path.write_text('{"version": "0.2", "repos": "invalid"}', encoding="utf-8")
    monkeypatch.setattr(spec_store, "DEFAULT_REPOS_SPEC_PATH", spec_path)
    snapshot = devops_status_data.collect_status_section("repos")
    assert snapshot.level == "error"
    assert snapshot.summary == "Check failed"


def test_inspection_handles_detached_unborn_and_bare_repositories(tmp_path: Path) -> None:
    detached_path = tmp_path / "detached"
    with _initialize_repository(detached_path) as repository:
        repository.git.checkout("--detach", "HEAD")
        detached = inspect_local_repository(destination=detached_path)
        assert detached.state == "Clean"
        assert detached.branch is None
        assert detached.committed_at is not None

    unborn_path = tmp_path / "unborn"
    with Repo.init(unborn_path, initial_branch="main"):
        unborn = inspect_local_repository(destination=unborn_path)
        assert unborn.state == "Clean"
        assert unborn.branch == "main"
        assert unborn.committed_at is None

    bare_path = tmp_path / "bare.git"
    with Repo.init(bare_path, bare=True, initial_branch="main"):
        bare = inspect_local_repository(destination=bare_path)
        assert bare.state == "Bare"
        assert bare.committed_at is None


def test_inspection_does_not_use_parent_repository(tmp_path: Path) -> None:
    with _initialize_repository(tmp_path):
        child = tmp_path / "ordinary-directory"
        child.mkdir()
        status = inspect_local_repository(destination=child)
    assert status.state == "Not a Git repo"


def test_staged_rename_consumes_old_path_and_counts_remaining_changes(tmp_path: Path) -> None:
    with _initialize_repository(tmp_path) as repository:
        repository.git.mv("tracked.txt", "renamed.txt")
        (tmp_path / "untracked.txt").write_text("new\n", encoding="utf-8")
        status = inspect_local_repository(destination=tmp_path)
    assert status.state == "Changed"
    assert status.changes == "1n/1r"
