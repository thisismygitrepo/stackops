
from typing import Annotated
import typer

from stackops.utils.source_of_truth import DOTFILES_SSL_ORIGIN_SERVER_CERT_PATH, DOTFILES_SSL_ORIGIN_SERVER_KEY_PATH, read_quick_password

"""
reference:
# https://github.com/tsl0922/ttyd/wiki/Serving-web-fonts
# -t "fontFamily=CaskaydiaCove" bash
# --terminal-type xterm-kitty

"""


def display_terminal_url(local_ip_v4: str, port: int, protocol: str = "http") -> None:
    """Display a flashy, unmissable terminal URL announcement."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.align import Align
    console = Console()
    # Create the main message with styling
    url_text = Text(f"{protocol}://{local_ip_v4}:{port}", style="bold bright_cyan underline")
    message = Text.assemble(
        ("🚀 ", "bright_red"),
        ("Terminal is now accessible at: ", "bright_white bold"),
        url_text,
        (" 🚀", "bright_red")
    )
    
    # Create a fancy panel with borders and styling
    panel = Panel(
        Align.center(message),
        title="[bold bright_green]🌐 WEB TERMINAL READY 🌐[/bold bright_green]",
        subtitle="[italic bright_yellow]⚡ Click the link above to access your terminal! ⚡[/italic bright_yellow]",
        border_style="bright_magenta",
        padding=(1, 2),
        expand=False
    )
    # Print with extra spacing and attention-grabbing elements
    # console.print("\n" + "🔥" * 60 + "\n", style="bright_red bold")
    console.print(panel)
    # console.print("🔥" * 60 + "\n", style="bright_red bold")


def share_terminal(
    port: Annotated[int | None, typer.Option("--port", "-p", help="Port to run the terminal server on (default: 7681)")] = None,
    username: Annotated[str | None, typer.Option("--username", "-u", help="Username for terminal access (default: current user)")] = None,
    password: Annotated[str | None, typer.Option("--password", "-w", help="Password for terminal access (default: configured quick password)")] = None,
    no_auth: Annotated[bool, typer.Option("--no-auth", "-n", help="Disable authentication (not recommended)")] = False,
    start_command: Annotated[str | None, typer.Option("--start-command", "-s", help="Command to run on terminal start (default: bash/powershell)")] = None,
    ssl: Annotated[bool, typer.Option("--ssl", "-S", help="Enable SSL")] = False,
    ssl_cert: Annotated[str | None, typer.Option("--ssl-cert", "-C", help="SSL certificate file path")] = None,
    ssl_key: Annotated[str | None, typer.Option("--ssl-key", "-K", help="SSL key file path")] = None,
    ssl_ca: Annotated[str | None, typer.Option("--ssl-ca", "-A", help="SSL CA file path for client certificate verification")] = None,
    over_internet: Annotated[bool, typer.Option("--over-internet", "-i", help="Expose the terminal over the internet using ngrok")] = False,
    install_missing_dependencies: Annotated[bool, typer.Option("--install-dep", "-D", help="Install missing dependencies", show_default=False)] = False,

) -> None:
    if install_missing_dependencies:
        from stackops.utils.installer_utils.installer_cli import install_if_missing
        install_if_missing(which="ttyd", binary_name=None, verbose=True)
    if over_internet and install_missing_dependencies:
        from stackops.utils.installer_utils.installer_cli import install_if_missing
        install_if_missing(which="ngrok", binary_name=None, verbose=True)

    from pathlib import Path
    if no_auth and (username is not None or password is not None):
        print("❌ Error: --no-auth cannot be combined with --username or --password.")
        raise typer.Exit(code=1)
    if not ssl and any(value is not None for value in (ssl_cert, ssl_key, ssl_ca)):
        print("❌ Error: --ssl-cert, --ssl-key, and --ssl-ca require --ssl.")
        raise typer.Exit(code=1)
    if username is None:
        import getpass
        username = getpass.getuser()
    if password is None and not no_auth:
        try:
            password = read_quick_password()
        except Exception:
            print("❌ Error: Password not provided and configured quick password could not be read.")
            raise typer.Exit(code=1)

    if port is None:
        port = 7681  # Default port for ttyd
    if port < 1 or port > 65535:
        print(f"❌ Error: Invalid port '{port}'. Port must be between 1 and 65535.")
        raise typer.Exit(code=1)

    # Handle SSL certificate defaults
    if ssl:
        if ssl_cert is None:
            ssl_cert = str(DOTFILES_SSL_ORIGIN_SERVER_CERT_PATH)
        if ssl_key is None:
            ssl_key = str(DOTFILES_SSL_ORIGIN_SERVER_KEY_PATH)
        
        # Verify SSL files exist
        cert_path = Path(ssl_cert)
        key_path = Path(ssl_key)
        
        if not cert_path.exists():
            print(f"❌ Error: SSL certificate file not found: {ssl_cert}")
            raise typer.Exit(code=1)
        if not key_path.exists():
            print(f"❌ Error: SSL key file not found: {ssl_key}")
            raise typer.Exit(code=1)
        
        if ssl_ca and not Path(ssl_ca).exists():
            print(f"❌ Error: SSL CA file not found: {ssl_ca}")
            raise typer.Exit(code=1)

    import stackops.scripts.python.helpers.helpers_network.address as helper
    res = helper.select_lan_ipv4(prefer_vpn=False)
    if res is None:
        print("❌ Error: Could not determine local LAN IPv4 address for terminal.")
        raise typer.Exit(code=1)
    local_ip_v4 = res

    # Display the flashy terminal announcement  
    protocol = "https" if ssl else "http"
    display_terminal_url(local_ip_v4, port, protocol)
    
    # Build ttyd command with SSL options
    ssl_args: list[str] = []
    if ssl:
            if ssl_cert is None or ssl_key is None:
                print("❌ Error: SSL certificate and key must be provided when SSL is enabled.")
                raise typer.Exit(code=1)
            resolved_ssl_cert = ssl_cert
            resolved_ssl_key = ssl_key
            ssl_args = ["--ssl", "--ssl-cert", resolved_ssl_cert, "--ssl-key", resolved_ssl_key]
            if ssl_ca:
                ssl_args.extend(["--ssl-ca", ssl_ca])

    if start_command is None:
        import platform
        if platform.system().lower() == "windows":
            start_command = "powershell"
        else:
            start_command = "bash"

    import shlex
    import subprocess
    import time
    start_command_parts = shlex.split(start_command)
    if not start_command_parts:
        print("❌ Error: --start-command must not be empty.")
        raise typer.Exit(code=1)

    ttyd_cmd = ["ttyd", "--writable", "-t", "enableSixel=true", *ssl_args, "--port", str(port)]
    if not no_auth:
        if password is None:
            print("❌ Error: Password not provided.")
            raise typer.Exit(code=1)
        ttyd_cmd.extend(["--credential", f"{username}:{password}"])
    ttyd_cmd.extend(["-t", """theme={"background": "black"}""", *start_command_parts])

    processes: dict[str, subprocess.Popen[bytes]] = {}
    try:
        try:
            processes["ttyd"] = subprocess.Popen(ttyd_cmd)
        except FileNotFoundError:
            print("❌ Error: ttyd was not found. Use --install-dep to install missing dependencies.")
            raise typer.Exit(code=1) from None

        if over_internet:
            try:
                processes["ngrok"] = subprocess.Popen(["ngrok", "http", str(port)])
            except FileNotFoundError:
                print("❌ Error: ngrok was not found. Use --install-dep to install missing dependencies.")
                raise typer.Exit(code=1) from None
            time.sleep(3)
            import json
            from urllib import error, request

            try:
                with request.urlopen("http://127.0.0.1:4040/api/tunnels", timeout=5) as response:
                    data = json.load(response)
            except (error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
                print(f"❌ Error: Could not retrieve ngrok URL: {exc}")
                raise typer.Exit(code=1) from exc

            tunnels = data.get("tunnels")
            if not isinstance(tunnels, list) or len(tunnels) == 0:
                print("❌ Error: Ngrok did not report any active tunnels.")
                raise typer.Exit(code=1)
            public_url = tunnels[0].get("public_url") if isinstance(tunnels[0], dict) else None
            if not isinstance(public_url, str) or public_url == "":
                print("❌ Error: Ngrok tunnel response did not include a public URL.")
                raise typer.Exit(code=1)
            print(f"🌐 Ngrok tunnel ready: {public_url}")

        while True:
            exited_processes = [f"{name} (exit code {process.returncode})" for name, process in processes.items() if process.poll() is not None]
            if exited_processes:
                print(f"❌ Error: Process exited unexpectedly: {', '.join(exited_processes)}")
                raise typer.Exit(code=1)
            print("Terminal server is running. Press Ctrl+C to stop.")
            time.sleep(2)
    except KeyboardInterrupt:
        print("\nTerminating processes...")
    finally:
        for process in processes.values():
            if process.poll() is None:
                process.terminate()
        for process in processes.values():
            process.wait()


def main_with_parser() -> None:
    typer.run(share_terminal)


if __name__ == "__main__":
    pass
