from typer.testing import CliRunner

import stackops.scripts.python.stackops_entry as stackops_entry_app


def test_stackops_fire_help_omits_removed_options() -> None:
    result = CliRunner().invoke(stackops_entry_app.get_app(), ["fire", "--help"])

    assert result.exit_code == 0
    assert "--zellij-tab" not in result.stdout
    assert "--submit-to-cloud" not in result.stdout


def test_stackops_fire_rejects_removed_options() -> None:
    result = CliRunner().invoke(stackops_entry_app.get_app(), ["fire", "--submit-to-cloud", "demo.py"])

    assert result.exit_code == 2
    assert isinstance(result.exception, SystemExit)
