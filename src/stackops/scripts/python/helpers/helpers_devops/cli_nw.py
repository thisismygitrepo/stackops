import typer
from typing import Annotated, Literal

from stackops.scripts.python.helpers.helpers_devops import (
    cli_device,
    cli_share_file,
    cli_share_server,
    cli_share_temp,
    cli_share_terminal,
    cli_ssh,
)


def show_address() -> None:
    """📌 Show this computer addresses on network"""
    import stackops.scripts.python.helpers.helpers_network.address as helper

    public_ip_address = "N/A"
    try:
        loaded_json = helper.get_public_ip_address()
        from rich import print_json

        print_json(data=loaded_json)
        public_ip_address = loaded_json["ip"]
    except Exception as e:
        print(f"⚠️  Could not fetch public IP address: {e}")

    from rich.table import Table
    from rich.console import Console

    addresses = helper.get_all_ipv4_addresses()
    addresses.append(("Public IP", public_ip_address))

    # loc = loaded_json["loc"]
    # cmd = f"""curl "https://maps.geoapify.com/v1/staticmap?style=osm-bright&width=600&height=300&center=lonlat:{loc}&zoom=6&marker=lonlat:{loc};color:%23ff0000;size:medium&apiKey=$GEOAPIFY_API_KEY" -o map.png && chafa map.png"""
    # from stackops.utils.code import run_shell_script
    # run_shell_script(script=cmd)

    table = Table(title="Network Interfaces")
    table.add_column("Interface", style="cyan")
    table.add_column("IP Address", style="green")

    for iface, ip in addresses:
        table.add_row(iface, ip)

    console = Console()
    console.print(table)

    selected_lan_ip = helper.select_lan_ipv4(prefer_vpn=False)
    if selected_lan_ip is not None:
        # ip, iface = res
        # print(f"Selected IP: {ip} on interface: {iface}")
        print(f"LAN IPv4: {selected_lan_ip}")
    else:
        print("No network interfaces found.")


def vscode_share(
    action: Annotated[
        Literal["run", "r", "install-service", "i", "uninstall-service", "u", "share-local", "l"],
        typer.Argument(..., help="Action to perform", case_sensitive=False, show_choices=True),
    ],
    name: Annotated[str | None, typer.Option("--name", "-n", help="Name for tunnel/service actions (run, install-service)")] = None,
    path: Annotated[str | None, typer.Option("--path", "-p", help="Server base path for local web mode (share-local)")] = None,
    host: Annotated[str, typer.Option("--host", "-h", help="Host for local web mode (share-local)")] = "0.0.0.0",
    directory: Annotated[
        str | None, typer.Option("--dir", "-d", help="Folder to open in local web mode (share-local), defaults to the current working directory")
    ] = None,
    extra_args: Annotated[str | None, typer.Option("--extra-args", "-e", help="Extra args to append to the generated VS Code command")] = None,
) -> None:
    """🧑‍💻 Share workspace using VS Code CLI ("code tunnel" / "code serve-web")

    Note: this helper prints recommended commands and optionally runs them.
    If you need more functionality, consult VS Code Tunnels docs: https://code.visualstudio.com/docs/remote/tunnels
    """
    accept = "--accept-server-license-terms"
    name_part = f"--name {name}" if name else ""
    extra = extra_args or ""
    action_normalized = {"r": "run", "i": "install-service", "u": "uninstall-service", "l": "share-local"}.get(action, action)
    match action_normalized:
        case "run" | "r":
            cmd = f"code tunnel {name_part} {accept} {extra}".strip()
            desc = "Run a one-off VS Code tunnel (foreground)"
        case "install-service" | "i":
            cmd = f"code tunnel service install {accept} {name_part}".strip()
            desc = "Install code tunnel as a service"
        case "uninstall-service" | "u":
            cmd = "code tunnel service uninstall"
            desc = "Uninstall code tunnel service"
        case "share-local" | "l":
            from stackops.scripts.python.helpers.helpers_devops.cli_nw_vscode_share import (
                ensure_without_connection_token,
                resolve_share_local_folder,
            )

            host_part = f"--host {host}" if host else ""
            server_base_path_part = f"--server-base-path {path}" if path else ""
            directory = resolve_share_local_folder(directory)
            extra = ensure_without_connection_token(extra)
            cmd = f"code serve-web {accept} {host_part} {server_base_path_part} {extra}".strip()
            desc = "Run local VS Code web server (serve-web)"
        case _:
            print(f"Unknown action: {action_normalized}")
            return
    from stackops.utils.code import print_code, exit_then_run_shell_script

    print_code(cmd, lexer="bash", desc=desc)
    if action_normalized == "share-local":
        from stackops.scripts.python.helpers.helpers_devops.cli_nw_vscode_share import print_serve_web_urls

        print_serve_web_urls(cmd, folder_path=directory)
        exit_then_run_shell_script(cmd)
        return
    exit_then_run_shell_script(cmd)


def get_app() -> typer.Typer:
    nw_apps = typer.Typer(help="🔐 <n> Network subcommands", no_args_is_help=True, add_help_option=True, add_completion=False)
    nw_apps.command(name="share-terminal", help="📡 <t> Share terminal via web browser")(cli_share_terminal.share_terminal)
    nw_apps.command(name="t", help="Share terminal via web browser", hidden=True)(cli_share_terminal.share_terminal)

    nw_apps.command(name="share-server", help="🌐 <s> Start local/global server to share files/folders via web browser", no_args_is_help=True)(
        cli_share_server.web_file_explorer
    )
    nw_apps.command(name="s", help="Start local/global server to share files/folders via web browser", hidden=True, no_args_is_help=True)(
        cli_share_server.web_file_explorer
    )

    # app = cli_share_server.get_share_file_app()
    # nw_apps.add_typer(app, name="share-file", help="📁 <f> Share a file via relay server", no_args_is_help=True)
    # nw_apps.add_typer(app, name="f", help="Share a file via relay server", hidden=True, no_args_is_help=True)
    nw_apps.command(name="send", no_args_is_help=True, hidden=False, help="📁 <sx> send files from here.")(cli_share_file.share_file_send)
    nw_apps.command(name="sx", no_args_is_help=True, hidden=True, help="📁 [sx] send files from here.")(cli_share_file.share_file_send)
    nw_apps.command(name="receive", no_args_is_help=True, hidden=False, help="📁 <rx> receive files to here.")(cli_share_file.share_file_receive)
    nw_apps.command(name="rx", no_args_is_help=True, hidden=True, help="📁 [rx] receive files to here.")(cli_share_file.share_file_receive)

    nw_apps.command(name="share-temp-file", help="🌡 <T> Share a file via temp.sh", no_args_is_help=True)(cli_share_temp.upload_file)
    nw_apps.command(name="T", help="Share a file via temp.sh", hidden=True, no_args_is_help=True)(cli_share_temp.upload_file)

    nw_apps.add_typer(cli_ssh.get_app(), name="ssh", help="🔐 <S> SSH subcommands")
    nw_apps.add_typer(cli_ssh.get_app(), name="S", help="SSH subcommands", hidden=True)
    nw_apps.add_typer(cli_device.get_app(), name="device", help="🖥 <d> Device subcommands")
    nw_apps.add_typer(cli_device.get_app(), name="d", help="Device subcommands", hidden=True)

    nw_apps.command(name="show-address", help="📌 <a> Show this computer addresses on network")(show_address)
    nw_apps.command(name="a", help="Show this computer addresses on network", hidden=True)(show_address)

    # VS Code Tunnels helper
    nw_apps.command(name="vscode-share", no_args_is_help=True, help="💻 <v> Share workspace via VS Code Tunnels")(vscode_share)
    nw_apps.command(name="v", no_args_is_help=True, hidden=True, help="Share workspace via VS Code Tunnels")(vscode_share)

    return nw_apps
