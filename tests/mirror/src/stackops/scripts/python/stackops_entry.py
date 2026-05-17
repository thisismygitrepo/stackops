import pytest
import typer
from typer.testing import CliRunner

import stackops.scripts.python.stackops_entry as stackops_entry_app
import stackops.scripts.python.utils as utils_app


def test_stackops_fire_help_omits_removed_options() -> None:
    result = CliRunner().invoke(stackops_entry_app.get_app(), ["fire", "--help"])

    assert result.exit_code == 0
    assert "--zellij-tab" not in result.stdout
    assert "--submit-to-cloud" not in result.stdout


def test_stackops_fire_rejects_removed_options() -> None:
    result = CliRunner().invoke(stackops_entry_app.get_app(), ["fire", "--submit-to-cloud", "demo.py"])

    assert result.exit_code == 2
    assert isinstance(result.exception, SystemExit)


def test_stackops_utils_propagates_nested_exit_code(monkeypatch: pytest.MonkeyPatch) -> None:
    pyproject_app = typer.Typer()

    @pyproject_app.command("test-reference")
    def test_reference() -> None:
        raise typer.Exit(code=7)

    fake_utils_app = typer.Typer()
    fake_utils_app.add_typer(pyproject_app, name="pyproject")

    def fake_get_app() -> typer.Typer:
        return fake_utils_app

    monkeypatch.setattr(utils_app, "get_app", fake_get_app)

    result = CliRunner().invoke(
        stackops_entry_app.get_app(),
        ["utils", "pyproject", "test-reference"],
    )

    assert result.exit_code == 7
    assert isinstance(result.exception, SystemExit)
