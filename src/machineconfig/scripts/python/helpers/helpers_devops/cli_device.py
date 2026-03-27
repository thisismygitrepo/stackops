from typing import Annotated, Literal

import typer


def switch_public_ip_address(
    wait_seconds: Annotated[float, typer.Option(..., "--wait", "-w", help="Seconds to wait between steps")] = 2.0,
    max_trials: Annotated[int, typer.Option(..., "--max-trials", "-m", help="Max number of switch attempts")] = 10,
    target_ip: Annotated[
        list[str] | None, typer.Option(..., "--target-ip", "-t", help="Acceptable target IPs, if current IP matches any, no switch needed")
    ] = None,
) -> None:
    """🔁 Switch public IP address (Cloudflare WARP)"""
    import machineconfig.scripts.python.helpers.helpers_network.address_switch as helper

    helper.switch_public_ip_address(max_trials=max_trials, wait_seconds=wait_seconds, target_ip_addresses=target_ip)


def bind_wsl_port(port: Annotated[int, typer.Option(..., "--port", "-p", help="Port number to bind")]) -> None:
    code = f"""

$wsl_ip = (wsl.exe hostname -I).Trim().Split(' ')[0]
netsh interface portproxy add v4tov4 listenport={port} listenaddress=0.0.0.0 connectport={port} connectaddress=$wsl_ip

"""
    from machineconfig.utils.code import exit_then_run_shell_script

    exit_then_run_shell_script(code)


def open_wsl_port(ports: Annotated[str, typer.Argument(..., help="Comma-separated ports or port ranges (e.g., '8080,3000-3005,443')")]) -> None:
    """🔥 Open Windows firewall ports for WSL (Windows only)."""
    import machineconfig.utils.ssh_utils.wsl as wsl_utils

    wsl_utils.open_wsl_port(ports)


def link_wsl_and_windows_home(
    windows_username: Annotated[
        str | None, typer.Option("--windows-username", "-u", help="Windows username to use (optional, auto-detected if not provided)")
    ] = None,
) -> None:
    """🔗 Link WSL home and Windows home directories."""
    import machineconfig.utils.ssh_utils.wsl as wsl_utils

    wsl_utils.link_wsl_and_windows(windows_username)


def wifi_select(
    ssid: Annotated[str, typer.Option("-n", "--ssid", help="🔗 SSID of WiFi (from config)")] = "MyPhoneHotSpot",
    manual: Annotated[bool, typer.Option("-m", "--manual", help="🔍 Manual network selection mode")] = False,
    list_: Annotated[bool, typer.Option("-l", "--list", help="📡 List available networks only")] = False,
) -> None:
    """Main function with fallback network selection"""
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Confirm

    from machineconfig.scripts.python.helpers.helpers_network.wifi_conn import (
        display_available_networks,
        manual_network_selection,
        try_config_connection,
    )

    console = Console()
    console.print(Panel("📶 Welcome to the WiFi Connector Tool", title="[bold blue]WiFi Connection[/bold blue]", border_style="blue"))

    if list_:
        display_available_networks()
        return

    if manual:
        console.print("[blue]🔍 Manual network selection mode[/blue]")
        if manual_network_selection():
            console.print("[green]🎉 Successfully connected![/green]")
        else:
            console.print("[red]❌ Failed to connect[/red]")
        return

    console.print(f"[blue]🔍 Attempting to connect to configured network: {ssid}[/blue]")

    if try_config_connection(ssid):
        console.print("[green]🎉 Successfully connected using configuration![/green]")
        return

    console.print("\n[yellow]⚠️  Configuration connection failed or not available[/yellow]")

    if Confirm.ask("[blue]Would you like to manually select a network?[/blue]", default=True):
        if manual_network_selection():
            console.print("[green]🎉 Successfully connected![/green]")
        else:
            console.print("[red]❌ Failed to connect[/red]")
    else:
        console.print("[blue]👋 Goodbye![/blue]")


def reset_cloudflare_tunnel(
    task: Annotated[
        Literal["oneoff-shell-process", "oneoff-background-process", "as-service"],
        typer.Option(..., "--task", "-t", help="Task to perform", case_sensitive=False, show_choices=True),
    ],
    tunnel_name: Annotated[str | None, typer.Option("--tunnel-name", "-n", help="Name of the Cloudflare tunnel to run")] = None,
) -> None:
    code = """
# cloudflared tunnel route dns glenn  # creates CNAMES in Cloudflare dashboard
# sudo systemctl stop cloudflared
"""
    match task:
        case "oneoff-shell-process":
            tunnel_name = tunnel_name or ""
            code = f"""cloudflared tunnel run {tunnel_name}  #  This is running like a normal command """
        case "oneoff-background-process":
            tunnel_name = tunnel_name or ""
            import getpass

            user_name = getpass.getuser()
            code = f"""
# This verion runs like a deamon, but its not peristent across reboots
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
    tunnel run {tunnel_name}
"""
        case "as-service":
            code = """
home_dir=$HOME
cloudflared_path="$home_dir/.local/bin/cloudflared"
sudo $cloudflared_path service uninstall
sudo rm /etc/cloudflared/config.yml || true
sudo $cloudflared_path --config $home_dir/.cloudflared/config.yml service install
"""

    from machineconfig.utils.code import exit_then_run_shell_script, print_code

    print_code(code, lexer="bash", desc="code to achieve the goal")
    yes = typer.confirm("Do you want to run the above commands now?", default=False)
    if yes:
        exit_then_run_shell_script(code)


def add_ip_exclusion_to_warp(ip: Annotated[str, typer.Option(..., "--ip", help="IP address(es) to exclude from WARP (Comma separated)")]) -> None:
    ips = ip.split(",")
    res = ""
    for an_ip in ips:
        res += f"""sudo warp-cli tunnel ip add {an_ip}
"""
        print(f"Adding IP exclusion to WARP for: {an_ip}")
    code = f"""
{res}
echo "Restarting WARP connection..."
sudo warp-cli disconnect
echo "Waiting for 2 seconds..."
sleep 2
echo "Reconnecting WARP..."
sudo warp-cli connect
"""
    print(code)
    print("NOTE: Please run the above commands in your terminal to apply the changes.")


def get_app() -> typer.Typer:
    device_app = typer.Typer(help="🖥 <d> Device subcommands", no_args_is_help=True, add_help_option=True, add_completion=False)
    device_app.command(name="switch-public-ip", help="🔁 <c> Switch public IP address (Cloudflare WARP)")(switch_public_ip_address)
    device_app.command(name="c", help="Switch public IP address (Cloudflare WARP)", hidden=True)(switch_public_ip_address)

    device_app.command(name="wifi-select", no_args_is_help=True, help="📶 <w> WiFi connection utility.")(wifi_select)
    device_app.command(name="w", no_args_is_help=True, hidden=True)(wifi_select)

    device_app.command(name="bind-wsl-port", help="🔌 <b> Bind WSL port to Windows host", no_args_is_help=True)(bind_wsl_port)
    device_app.command(name="b", help="Bind WSL port to Windows host", hidden=True, no_args_is_help=True)(bind_wsl_port)

    device_app.command(name="open-wsl-port", no_args_is_help=True, help="🔥 <o> Open Windows firewall ports for WSL.", hidden=False)(open_wsl_port)
    device_app.command(name="o", no_args_is_help=True, help="Open Windows firewall ports for WSL.", hidden=True)(open_wsl_port)

    device_app.command(name="link-wsl-windows", no_args_is_help=False, help="🔗 <l> Link WSL home and Windows home directories.", hidden=False)(
        link_wsl_and_windows_home
    )
    device_app.command(name="l", no_args_is_help=False, help="Link WSL home and Windows home directories.", hidden=True)(link_wsl_and_windows_home)

    device_app.command(name="reset-cloudflare-tunnel", help="☁ <r> Reset Cloudflare tunnel service")(reset_cloudflare_tunnel)
    device_app.command(name="r", help="Reset Cloudflare tunnel service", hidden=True)(reset_cloudflare_tunnel)

    device_app.command(name="add-ip-exclusion-to-warp", help="🚫 <p> Add IP exclusion to WARP")(add_ip_exclusion_to_warp)
    device_app.command(name="p", help="Add IP exclusion to WARP", hidden=True)(add_ip_exclusion_to_warp)
    return device_app
