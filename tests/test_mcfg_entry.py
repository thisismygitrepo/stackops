from typer.testing import CliRunner

from machineconfig.scripts.python import mcfg_entry


runner = CliRunner()


def test_mcfg_help_lists_terminal_and_seek() -> None:
    result = runner.invoke(mcfg_entry.get_app(), ["--help"])

    assert result.exit_code == 0
    assert "terminal" in result.output
    assert "seek" in result.output


def test_terminal_short_alias_dispatches_to_terminal_help() -> None:
    result = runner.invoke(mcfg_entry.get_app(), ["t", "--help"])

    assert result.exit_code == 0
    assert "run-all" in result.output
    assert "trace" in result.output


def test_seek_short_alias_dispatches_to_seek_help() -> None:
    result = runner.invoke(mcfg_entry.get_app(), ["s", "--help"])

    assert result.exit_code == 0
    assert "--symantic" in result.output
    assert "--file" in result.output
