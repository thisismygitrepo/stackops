from typer.testing import CliRunner

from machineconfig.scripts.python import devops as devops_cli


runner = CliRunner()


def test_network_help_exposes_device_group_instead_of_device_commands() -> None:
    result = runner.invoke(devops_cli.get_app(), ["network", "--help"])

    assert result.exit_code == 0
    assert "device" in result.stdout
    assert "Device subcommands" in result.stdout
    assert "switch-public-ip" not in result.stdout
    assert "wifi-select" not in result.stdout
    assert "bind-wsl-port" not in result.stdout


def test_network_device_help_lists_moved_commands() -> None:
    result = runner.invoke(devops_cli.get_app(), ["network", "device", "--help"])

    assert result.exit_code == 0
    assert "switch-public-ip" in result.stdout
    assert "wifi-select" in result.stdout
    assert "bind-wsl-port" in result.stdout
    assert "open-wsl-port" in result.stdout
    assert "link-wsl-windows" in result.stdout
    assert "reset-cloudflare-tunnel" in result.stdout
    assert "add-ip-exclusion-to-warp" in result.stdout


def test_network_no_longer_exposes_moved_device_commands_at_top_level() -> None:
    result = runner.invoke(devops_cli.get_app(), ["network", "switch-public-ip", "--help"])

    assert result.exit_code != 0
    assert "No such command 'switch-public-ip'" in result.output
