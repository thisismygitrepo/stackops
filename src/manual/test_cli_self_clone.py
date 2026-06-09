from inspect import Parameter, signature
from pathlib import Path
from typing import get_args

from typer.testing import CliRunner

from stackops.scripts.python.helpers.helpers_devops import cli_self


def test_self_clone_command_is_registered() -> None:
    runner = CliRunner()

    help_result = runner.invoke(cli_self.get_app(), ["--help"])
    alias_result = runner.invoke(cli_self.get_app(), ["c", "--help"])

    assert help_result.exit_code == 0
    assert "clone" in help_result.stdout
    assert "<c>" in help_result.stdout
    assert alias_result.exit_code == 0
    assert "--remote" in alias_result.stdout
    assert "--dry-run" in alias_result.stdout


def test_self_clone_options_have_nice_aliases() -> None:
    parameters = signature(cli_self.clone).parameters
    expected_aliases = {
        "remote": "-r",
        "branch": "-b",
        "depth": "-d",
        "pull": "-p",
        "install_editable": "-i",
        "dry_run": "-n",
    }

    for parameter_name, alias in expected_aliases.items():
        assert alias in _option_param_decls(parameters[parameter_name])


def test_self_clone_defaults_to_current_directory(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(
        cli_self.get_app(),
        ["clone", "--dry-run", "--ssh", "--branch", "main", "--depth", "1"],
    )

    assert result.exit_code == 0
    assert f"git clone --branch main --depth 1 git@github.com:thisismygitrepo/stackops.git {tmp_path}" in result.stdout
    assert "Dry run only" in result.stdout
    assert not tmp_path.joinpath(".git").exists()


def _option_param_decls(parameter: Parameter) -> tuple[str, ...]:
    for metadata in get_args(parameter.annotation)[1:]:
        param_decls = getattr(metadata, "param_decls", ())
        if param_decls:
            return tuple(param_decls)
    raise AssertionError(f"Parameter has no Typer option metadata: {parameter.name}")
