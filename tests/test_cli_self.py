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


def test_status_help_lists_section_flags() -> None:
    result = runner.invoke(cli_self.get_app(), ["status", "--help"])

    assert result.exit_code == 0
    assert "--apps" in result.output
    assert "--shell" in result.output
    assert "--repos" in result.output
    assert "--dotfiles" in result.output
    assert "--backup" in result.output


def test_status_command_passes_selected_sections_to_helper() -> None:
    with (
        patch("machineconfig.scripts.python.helpers.helpers_devops.devops_status.resolve_sections", return_value=("apps",)) as resolve_sections,
        patch("machineconfig.scripts.python.helpers.helpers_devops.devops_status.main") as status_main,
    ):
        result = runner.invoke(cli_self.get_app(), ["status", "--apps"])

    assert result.exit_code == 0
    resolve_sections.assert_called_once_with(machine=False, shell=False, repos=False, ssh=False, configs=False, apps=True, backup=False)
    status_main.assert_called_once_with(sections=("apps",))
