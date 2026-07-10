from typing import Annotated

import typer


def bind_wsl_port(port: Annotated[int, typer.Option(..., "--port", "-p", min=1, max=65535, help="Port number to bind")]) -> None:
    code = f"""
if ! command -v netsh.exe >/dev/null 2>&1; then
  echo "netsh.exe is not available. Run this command from WSL on Windows."
  exit 1
fi

if ! command -v ip >/dev/null 2>&1; then
  echo "ip is not available. Run this command from WSL."
  exit 1
fi

wsl_ip="$(ip -4 route get 1.1.1.1 | sed -nE 's/.* src ([0-9.]+).*/\\1/p' | head -n 1)"
if [ -z "$wsl_ip" ]; then
  echo "Could not detect the WSL IPv4 address from the default route."
  exit 1
fi

netsh.exe interface portproxy delete v4tov4 listenport={port} listenaddress=0.0.0.0 >/dev/null 2>&1
netsh.exe interface portproxy add v4tov4 listenport={port} listenaddress=0.0.0.0 connectport={port} connectaddress="$wsl_ip"

"""
    import os
    from pathlib import Path

    from stackops.utils.code import exit_then_run_shell_script, run_shell_script

    op_program_path_raw = os.environ.get("OP_PROGRAM_PATH")
    if op_program_path_raw is not None and not Path(op_program_path_raw).exists():
        exit_then_run_shell_script(code)
    proc = run_shell_script(code, display_script=True, clean_env=False)
    if proc.returncode != 0:
        raise typer.Exit(code=proc.returncode)


def open_wsl_port(ports: Annotated[str, typer.Argument(..., help="Comma-separated ports or port ranges (e.g., '8080,3000-3005,443')")]) -> None:
    """🔥 Open Windows firewall ports for WSL (Windows only)."""
    import stackops.utils.ssh_utils.wsl as wsl_utils

    wsl_utils.open_wsl_port(ports)


def link_wsl_and_windows_home(
    windows_username: Annotated[
        str | None, typer.Option("--windows-username", "-u", help="Windows username to use (optional, auto-detected if not provided)")
    ] = None,
) -> None:
    """🔗 Link WSL home and Windows home directories."""
    import stackops.utils.ssh_utils.wsl as wsl_utils

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

    from stackops.scripts.python.helpers.helpers_network.wifi_conn import display_available_networks, manual_network_selection, try_config_connection

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


def get_app() -> typer.Typer:
    device_app = typer.Typer(help="🖥 <d> Device subcommands", no_args_is_help=True, add_help_option=True, add_completion=False)
    device_app.command(name="wifi-select", no_args_is_help=False, help="📶 <w> WiFi connection utility.")(wifi_select)
    device_app.command(name="w", no_args_is_help=False, hidden=True)(wifi_select)

    device_app.command(name="bind-wsl-port", help="🔌 <b> Bind WSL port to Windows host", no_args_is_help=True)(bind_wsl_port)
    device_app.command(name="b", help="Bind WSL port to Windows host", hidden=True, no_args_is_help=True)(bind_wsl_port)

    device_app.command(name="open-wsl-port", no_args_is_help=True, help="🔥 <o> Open Windows firewall ports for WSL.", hidden=False)(open_wsl_port)
    device_app.command(name="o", no_args_is_help=True, help="Open Windows firewall ports for WSL.", hidden=True)(open_wsl_port)

    device_app.command(name="link-wsl-windows", no_args_is_help=False, help="🔗 <l> Link WSL home and Windows home directories.", hidden=False)(
        link_wsl_and_windows_home
    )
    device_app.command(name="l", no_args_is_help=False, help="Link WSL home and Windows home directories.", hidden=True)(link_wsl_and_windows_home)
    return device_app
