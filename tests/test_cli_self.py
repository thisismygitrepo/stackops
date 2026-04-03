from unittest.mock import patch

from typer.testing import CliRunner

from machineconfig.scripts.python.helpers.helpers_devops import cli_self


runner = CliRunner()


def test_self_help_lists_export_and_interactive_commands() -> None:
    result = runner.invoke(cli_self.get_app(), ["--help"])

    assert result.exit_code == 0
    assert "export" in result.output
    assert "interactive" in result.output


def test_install_help_no_longer_shows_export_or_interactive_flags() -> None:
    result = runner.invoke(cli_self.get_app(), ["install", "--help"])

    assert result.exit_code == 0
    assert "--dev" in result.output
    assert "--export" not in result.output
    assert "--interactive" not in result.output


def test_export_command_calls_offline_export() -> None:
    with patch("machineconfig.utils.installer_utils.installer_offline.export") as export_installation_files:
        result = runner.invoke(cli_self.get_app(), ["export"])

    assert result.exit_code == 0
    export_installation_files.assert_called_once_with()


def test_interactive_command_calls_interactive_main() -> None:
    with patch("machineconfig.scripts.python.helpers.helpers_devops.interactive.main") as interactive_main:
        result = runner.invoke(cli_self.get_app(), ["interactive"])

    assert result.exit_code == 0
    interactive_main.assert_called_once_with()
