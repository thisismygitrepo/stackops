from pathlib import Path
from typing import cast

from git.repo import Repo
from typer.testing import CliRunner

from stackops.scripts.python.helpers.helpers_devops.cli_repos import get_app


def _initialize_repository(repository_path: Path) -> Repo:
    repository = Repo.init(repository_path, initial_branch="main")
    with repository.config_writer() as config:
        config.set_value("user", "name", "Stackops Tests")
        config.set_value("user", "email", "stackops-tests@example.invalid")
    tracked_file = repository_path.joinpath("tracked.txt")
    tracked_file.write_text("target\n", encoding="utf-8")
    repository.index.add([tracked_file.as_posix()])
    repository.index.commit("target")
    return repository


def test_version_help_exposes_declare_status_and_checkout() -> None:
    runner = CliRunner()

    repositories_help = runner.invoke(get_app(), ["--help"], terminal_width=180)
    version_help = runner.invoke(get_app(), ["version", "--help"], terminal_width=180)

    assert repositories_help.exit_code == 0
    assert "version" in repositories_help.output
    assert version_help.exit_code == 0
    assert "declare" in version_help.output
    assert "status" in version_help.output
    assert "checkout" in version_help.output


def test_version_commands_declare_inspect_and_preview_checkout_without_mutation(tmp_path: Path) -> None:
    workspace = tmp_path.joinpath("workspace")
    repository_path = workspace.joinpath("application")
    repository = _initialize_repository(repository_path=repository_path)
    runner = CliRunner()

    declare_result = runner.invoke(get_app(), ["version", "declare", "release-1", "--message", "First release", "--directory", workspace.as_posix()])

    assert declare_result.exit_code == 0
    assert "Declared version 'release-1'" in declare_result.output
    assert workspace.joinpath("versions.json").is_file()

    tracked_file = repository_path.joinpath("tracked.txt")
    tracked_file.write_text("current\n", encoding="utf-8")
    repository.index.add([tracked_file.as_posix()])
    current_commit = cast(str, repository.index.commit("current").hexsha).lower()

    status_result = runner.invoke(get_app(), ["version", "status", "release-1", "--directory", workspace.as_posix()], terminal_width=200)
    checkout_result = runner.invoke(
        get_app(), ["version", "checkout", "release-1", "--directory", workspace.as_posix(), "--dry-run"], terminal_width=200
    )

    assert status_result.exit_code == 0
    assert "Different" in status_result.output
    assert checkout_result.exit_code == 0
    assert "Checkout preview" in checkout_result.output
    assert "Would checkout" in checkout_result.output
    assert cast(str, repository.head.commit.hexsha).lower() == current_commit
