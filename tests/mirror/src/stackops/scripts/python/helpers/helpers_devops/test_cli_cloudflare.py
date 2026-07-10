from typer.testing import CliRunner

from stackops.scripts.python.helpers.helpers_devops import cli_device, cli_nw


CLOUDFLARE_COMMAND_NAMES: tuple[str, ...] = (
    "switch-public-ip",
    "reset-cloudflare-tunnel",
    "add-ip-exclusion-to-warp",
    "cloudflare-tunnel-status",
    "update-cloudflare-connectors",
    "sync-cloudflare-routes",
)


def test_network_owns_cloudflare_subcommands_and_device_does_not() -> None:
    runner = CliRunner()
    network_app = cli_nw.get_app()

    network_result = runner.invoke(network_app, ["--help"], terminal_width=160)
    cloudflare_result = runner.invoke(network_app, ["cloudflare", "--help"], terminal_width=160)
    cloudflare_alias_result = runner.invoke(network_app, ["c", "--help"], terminal_width=160)
    device_result = runner.invoke(cli_device.get_app(), ["--help"], terminal_width=160)

    assert network_result.exit_code == 0, network_result.output
    assert cloudflare_result.exit_code == 0, cloudflare_result.output
    assert cloudflare_alias_result.exit_code == 0, cloudflare_alias_result.output
    assert device_result.exit_code == 0, device_result.output
    assert "cloudflare" in network_result.output
    assert "☁ <c> Cloudflare subcommands" in network_result.output
    assert "\n│ c " not in network_result.output
    for command_name in CLOUDFLARE_COMMAND_NAMES:
        assert command_name in cloudflare_result.output
        assert command_name not in device_result.output
