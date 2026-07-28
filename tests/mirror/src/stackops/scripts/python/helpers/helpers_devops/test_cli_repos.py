from pathlib import Path

import pytest
from git.repo import Repo
from typer.testing import CliRunner

from stackops.scripts.python.helpers.helpers_devops.cli_repos import get_app


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


def test_action_help_includes_safety_options() -> None:
    result = CliRunner().invoke(get_app(), ["a", "--help"], terminal_width=180)

    assert result.exit_code == 0
    assert "--status" in result.output
    assert "Show status across repositories." in result.output
    assert "--message" in result.output
    assert "--dry-run" in result.output


@pytest.mark.parametrize(
    ("arguments", "expected_error"),
    [
        (["--status", "--pull"], "--status cannot be combined"),
        (["--push", "--uv-sync"], "--uv-sync requires --pull"),
        (["--commit"], "--commit requires a non-empty --message"),
        (["--push", "--message", "unused"], "--message can only be used with --commit"),
        (["--status", "--dry-run"], "--dry-run cannot be used"),
    ],
)
def test_action_rejects_invalid_option_combinations(arguments: list[str], expected_error: str) -> None:
    result = CliRunner().invoke(get_app(), ["a", *arguments])

    assert result.exit_code == 1
    assert expected_error in result.output


def test_failed_operation_returns_nonzero_exit_code(tmp_path: Path) -> None:
    repository_path = tmp_path / "repository"
    _initialize_repository(repository_path)

    result = CliRunner().invoke(get_app(), ["a", repository_path.as_posix(), "--push"])

    assert result.exit_code == 1
    assert "No remotes configured" in result.output


def test_commit_dry_run_does_not_create_commit(tmp_path: Path) -> None:
    repository_path = tmp_path / "repository"
    repository = _initialize_repository(repository_path)
    tracked_file = repository_path / "tracked.txt"
    tracked_file.write_text("changed\n")
    repository.index.add([tracked_file.as_posix()])
    commit_before = repository.head.commit.hexsha

    result = CliRunner().invoke(get_app(), ["a", repository_path.as_posix(), "--commit", "--message", "update", "--dry-run"])

    assert result.exit_code == 0
    assert "DRY RUN" in result.output
    assert repository.head.commit.hexsha == commit_before
    assert repository.index.diff("HEAD")
