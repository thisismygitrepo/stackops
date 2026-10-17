from typing import Annotated

import typer

from stackops.utils.constants import IS_REPO_DEVELOPER


def switch_public_ip_address(
    wait_seconds: Annotated[float, typer.Option(..., "--wait", "-w", min=0.0, help="Seconds to wait between steps")] = 2.0,
    max_trials: Annotated[int, typer.Option(..., "--max-trials", "-m", min=1, help="Max number of switch attempts")] = 10,
    target_ip: Annotated[
        list[str] | None, typer.Option(..., "--target-ip", "-t", help="Acceptable target IPs, if current IP matches any, no switch needed")
    ] = None,
) -> None:
    """🔁 Switch public IP address (Cloudflare WARP)"""
    import stackops.scripts.python.helpers.helpers_network.address_switch as helper

    helper.switch_public_ip_address(max_trials=max_trials, wait_seconds=wait_seconds, target_ip_addresses=target_ip)


def run_tunnel(
    tunnel_name: Annotated[str | None, typer.Option("--tunnel-name", "-n", help="Name of the Cloudflare tunnel to run")] = None,
    background: Annotated[bool, typer.Option("--background", "-b", help="Run as a transient systemd service instead of in the foreground.")] = False,
) -> None:
    import shlex

    tunnel_argument = shlex.quote(tunnel_name) if tunnel_name is not None else ""
    if background:
        import getpass

        user_name = getpass.getuser()
        code = f"""
sudo systemd-run \
  --unit=cloudflared-tunnel \
  --description="Cloudflared Tunnel (transient)" \
  --property=Restart=on-failure \
  --property=RestartSec=5 \
  --property=User={user_name} \
  --property=Group={user_name} \
  --property=Environment=HOME=/home/{user_name} \
  --property=WorkingDirectory=/home/{user_name} \
  /home/{user_name}/.local/bin/cloudflared \
    --config /home/{user_name}/.cloudflared/config.yml \
    tunnel run {tunnel_argument}
"""
    else:
        code = f"""cloudflared tunnel run {tunnel_argument}"""

    from stackops.utils.code import exit_then_run_shell_script
    from stackops.utils.meta import print_code

    if IS_REPO_DEVELOPER:
        print_code(code, lexer="bash", desc="Run the Cloudflare tunnel")
    if typer.confirm("Run the Cloudflare tunnel now?", default=False):
        exit_then_run_shell_script(code)


def reinstall_tunnel_service() -> None:
    code = """
devops software install --update cloudflared
stackops_tunnel_home=$HOME
cloudflared_path="$stackops_tunnel_home/.local/bin/cloudflared"
sudo $cloudflared_path service uninstall
sudo rm /etc/cloudflared/config.yml || true
sudo $cloudflared_path --config $stackops_tunnel_home/.cloudflared/config.yml service install
"""

    from stackops.utils.code import exit_then_run_shell_script
    from stackops.utils.meta import print_code

    if IS_REPO_DEVELOPER:
        print_code(code, lexer="bash", desc="Reinstall the Cloudflare tunnel service")
    if typer.confirm("Reinstall the Cloudflare tunnel service now?", default=False):
        exit_then_run_shell_script(code)


def add_ip_exclusion_to_warp(
    ip: Annotated[str, typer.Option(..., "--ip", "-i", help="IP address(es) to exclude from WARP (Comma separated)")],
) -> None:
    from ipaddress import IPv4Address, IPv6Address, ip_address

    ips: list[IPv4Address | IPv6Address] = []
    for raw_ip in ip.split(","):
        stripped_ip = raw_ip.strip()
        if not stripped_ip:
            continue
        try:
            ips.append(ip_address(stripped_ip))
        except ValueError as error:
            raise typer.BadParameter(str(error), param_hint="--ip") from error
    if len(ips) == 0:
        raise typer.BadParameter("Provide at least one IP address.", param_hint="--ip")

    exclusion_commands = "\n".join(f"sudo warp-cli tunnel ip add {excluded_ip}" for excluded_ip in ips)
    code = f"""
{exclusion_commands}
echo "Restarting WARP connection..."
sudo warp-cli disconnect
echo "Waiting for 2 seconds..."
sleep 2
echo "Reconnecting WARP..."
sudo warp-cli connect
"""
    from stackops.utils.code import exit_then_run_shell_script
    from stackops.utils.meta import print_code

    if IS_REPO_DEVELOPER:
        print_code(code, lexer="bash", desc="code to achieve the goal")
    yes = typer.confirm("Add the IP exclusions and restart WARP now?", default=False)
    if yes:
        exit_then_run_shell_script(code)


def get_app() -> typer.Typer:
    from stackops.scripts.python.helpers.helpers_devops import cli_cloudflare_tunnel

    cloudflare_app = typer.Typer(
        help="☁ Cloudflare subcommands", no_args_is_help=True, add_help_option=True, add_completion=False,
        context_settings={"help_option_names": ["-h", "--help"]},
    )
    cloudflare_app.command(name="switch-public-ip", help="🔁 <s> Switch public IP address (Cloudflare WARP)")(switch_public_ip_address)
    cloudflare_app.command(name="s", help="Switch public IP address (Cloudflare WARP)", hidden=True)(switch_public_ip_address)
    cloudflare_app.command(name="run-tunnel", help="🚀 <r> Run a Cloudflare tunnel in the foreground or background.")(run_tunnel)
    cloudflare_app.command(name="r", hidden=True)(run_tunnel)
    cloudflare_app.command(name="reinstall-tunnel-service", help="🔄 <R> Reinstall the persistent Cloudflare tunnel service.")(reinstall_tunnel_service)
    cloudflare_app.command(name="R", hidden=True)(reinstall_tunnel_service)
    cloudflare_app.command(name="add-ip-exclusion-to-warp", help="🚫 <p> Add IP exclusion to WARP")(add_ip_exclusion_to_warp)
    cloudflare_app.command(name="p", help="Add IP exclusion to WARP", hidden=True)(add_ip_exclusion_to_warp)
    cloudflare_app.command(name="tunnel-status", help="📊 <t> Show tunnel redundancy, versions, services, and routes")(
        cli_cloudflare_tunnel.cloudflare_tunnel_status
    )
    cloudflare_app.command(name="t", help="Show Cloudflare Tunnel status", hidden=True)(cli_cloudflare_tunnel.cloudflare_tunnel_status)
    cloudflare_app.command(name="update-connectors", help="⏫ <u> Rolling-update Cloudflare Tunnel connectors")(
        cli_cloudflare_tunnel.update_cloudflare_connectors
    )
    cloudflare_app.command(name="u", help="Rolling-update Cloudflare Tunnel connectors", hidden=True)(
        cli_cloudflare_tunnel.update_cloudflare_connectors
    )
    cloudflare_app.command(name="sync-routes", help="🔀 <y> Copy selected ingress routes without tunnel credentials")(
        cli_cloudflare_tunnel.sync_cloudflare_routes
    )
    cloudflare_app.command(name="y", help="Copy selected Cloudflare Tunnel ingress routes", hidden=True)(cli_cloudflare_tunnel.sync_cloudflare_routes)
    return cloudflare_app
