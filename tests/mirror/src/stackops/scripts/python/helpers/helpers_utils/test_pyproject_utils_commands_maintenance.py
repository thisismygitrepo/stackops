from pathlib import Path
import subprocess

import pytest
from typer.testing import CliRunner

from stackops.scripts.python.helpers.helpers_devops import cli_repos
from stackops.scripts.python.helpers.helpers_utils import pyproject_utils_app


@pytest.mark.parametrize(
    ("command_name", "expected_option"),
    [
        ("config-linters", "--linter"),
        ("l", "--linter"),
        ("cleanup", "--recursive"),
        ("n", "--recursive"),
    ],
)
def test_maintenance_commands_are_registered_under_pyproject(command_name: str, expected_option: str) -> None:
    result = CliRunner().invoke(pyproject_utils_app.get_app(), [command_name, "--help"])

    assert result.exit_code == 0, result.output
    assert expected_option in result.output


def test_maintenance_commands_are_not_registered_under_repos() -> None:
    runner = CliRunner()
    help_result = runner.invoke(cli_repos.get_app(), ["--help"])

    assert help_result.exit_code == 0, help_result.output
    assert "config-linters" not in help_result.output
    assert "cleanup" not in help_result.output

    for removed_command in ("config-linters", "l", "cleanup", "n"):
        result = runner.invoke(cli_repos.get_app(), [removed_command, "--help"])

        assert result.exit_code != 0, result.output
        assert f"No such command '{removed_command}'" in result.output


def test_config_linters_resolves_templates_after_module_move(tmp_path: Path) -> None:
    repo_root = tmp_path.joinpath("repo")
    nested_directory = repo_root.joinpath("nested")
    nested_directory.mkdir(parents=True)
    subprocess.run(["git", "init", "--quiet"], cwd=repo_root, check=True)

    result = CliRunner().invoke(
        pyproject_utils_app.get_app(),
        ["config-linters", str(nested_directory), "--linter", "ruff"],
    )

    assert result.exit_code == 0, result.output
    assert repo_root.joinpath(".ruff.toml").is_file()
    assert not nested_directory.joinpath(".ruff.toml").exists()
