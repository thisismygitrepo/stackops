from typing import Annotated
from pathlib import Path

import typer


def bind_wsl_port(port: Annotated[int, typer.Argument(help="Port number to bind", min=1, max=65535)]) -> None:
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


def connect_wifi(
    ssid: Annotated[str | None, typer.Option("-n", "--ssid", help="Exact SSID, or configured WiFi login name when no password source is supplied.")] = None,
    manual: Annotated[bool, typer.Option("-m", "--manual", help="🔍 Manual network selection mode")] = False,
    list_: Annotated[bool, typer.Option("-l", "--list", help="📡 List available networks only")] = False,
    password_file: Annotated[Path | None, typer.Option("--password-file", "-f", help="Read the network password from a file; '-' reads stdin.")] = None,
    password_env: Annotated[str | None, typer.Option("--password-env", "-E", help="Environment variable containing the network password.")] = None,
    output_json: Annotated[bool, typer.Option("--json", "-j", help="Print network inventory or connection receipt as JSON.")] = False,
) -> None:
    import json
    import subprocess

    from stackops.utils.cli_utils.interaction import require_interactive
    from stackops.utils.cli_utils.secret_input import read_secret_input

    if list_ and (ssid is not None or manual or password_file is not None or password_env is not None):
        raise typer.BadParameter("--list cannot be combined with connection options.")
    if manual:
        if ssid is not None or password_file is not None or password_env is not None or output_json:
            raise typer.BadParameter("--manual cannot be combined with an SSID, password source, or --json.")
        require_interactive("WiFi network selection; use --ssid and a password source")
    if not list_ and not manual and not ssid:
        raise typer.BadParameter("Provide --ssid, --manual, or --list.")
    if password_file is not None and password_env is not None:
        raise typer.BadParameter("Choose one of --password-file and --password-env.")

    from stackops.scripts.python.helpers.helpers_network.wifi_conn import connect_to_new_network, get_available_networks, manual_network_selection, try_config_connection
    from stackops.scripts.python.helpers.helpers_network.wifi_conn_platforms.common import render_networks_table

    try:
        if list_:
            networks = get_available_networks()
            if output_json:
                typer.echo(json.dumps(networks, indent=2))
            else:
                render_networks_table(networks, title="Available WiFi Networks")
            return
        if manual:
            if not manual_network_selection():
                raise typer.Exit(1)
        elif ssid is not None:
            if password_file is not None or password_env is not None:
                password = read_secret_input(value=None, file=password_file, env=password_env, prompt="WiFi password")
                connect_to_new_network(ssid, password)
            elif not try_config_connection(ssid):
                raise typer.BadParameter("Configured WiFi connection failed; supply --ssid and --password-file or --password-env.")
    except subprocess.CalledProcessError as error:
        typer.echo(f"WiFi operation failed with exit code {error.returncode}.", err=True)
        raise typer.Exit(1) from None
    except (OSError, RuntimeError) as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from None
    if output_json:
        typer.echo(json.dumps({"status": "connected", "ssid": ssid}))
    else:
        typer.echo("WiFi connection completed.")


def get_app() -> typer.Typer:
    device_app = typer.Typer(
        help="📱 <d> Device subcommands", no_args_is_help=True, add_help_option=True, add_completion=False,
        context_settings={"help_option_names": ["-h", "--help"]},
    )
    device_app.command(name="connect-wifi", no_args_is_help=False, help="📶 <c> Connect to a configured or selected WiFi network.")(connect_wifi)
    device_app.command(name="c", no_args_is_help=False, hidden=True)(connect_wifi)

    device_app.command(name="bind-wsl-port", help="🔌 <b> Bind WSL port to Windows host", no_args_is_help=True)(bind_wsl_port)
    device_app.command(name="b", help="Bind WSL port to Windows host", hidden=True, no_args_is_help=True)(bind_wsl_port)

    device_app.command(name="open-wsl-port", no_args_is_help=True, help="🔥 <o> Open Windows firewall ports for WSL.", hidden=False)(open_wsl_port)
    device_app.command(name="o", no_args_is_help=True, help="Open Windows firewall ports for WSL.", hidden=True)(open_wsl_port)

    device_app.command(name="link-wsl-windows", no_args_is_help=False, help="🔗 <l> Link WSL home and Windows home directories.", hidden=False)(
        link_wsl_and_windows_home
    )
    device_app.command(name="l", no_args_is_help=False, help="Link WSL home and Windows home directories.", hidden=True)(link_wsl_and_windows_home)
    return device_app
