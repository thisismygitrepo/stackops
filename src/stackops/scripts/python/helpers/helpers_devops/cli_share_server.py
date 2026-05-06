import shlex
from pathlib import Path
from typing import Annotated

import typer

from stackops.scripts.python.helpers.helpers_devops.cli_share_file import share_file_receive, share_file_send
from stackops.utils.accessories import display_with_flashy_style


def web_file_explorer(
    path: Annotated[str, typer.Argument(help="Path to the file or directory to share")],
    port: Annotated[int | None, typer.Option("--port", "-p", help="Port to run the share server on (default: 8080)")] = None,
    username: Annotated[str | None, typer.Option("--username", "-u", help="Username for share access (default: current user)")] = None,
    no_auth: Annotated[bool, typer.Option("--no-auth", "-na", help="Disable authentication for share access")] = False,
    password: Annotated[str | None, typer.Option("--password", "-w", help="Password for share access (default: from ~/dotfiles/creds/passwords/quick_password)")] = None,
    bind_address: Annotated[str, typer.Option("--bind", "-a", help="Address to bind the server to")] = "0.0.0.0",
    over_internet: Annotated[bool, typer.Option("--over-internet", "-i", help="Expose the share server over the internet using ngrok")] = False,
    backend: Annotated[str, typer.Option("--backend", "-b", help="Backend to use: filebrowser (default), miniserve, qrcp, or easy-sharing")] = "miniserve",
    install_missing_dependencies: Annotated[bool, typer.Option("--install-dep", "-D", help="Install missing dependencies", show_default=False)] = False,
) -> None:
    from stackops.utils.installer_utils.installer_cli import install_if_missing

    if backend not in ["filebrowser", "miniserve", "qrcp", "easy-sharing"]:
        typer.echo(f"❌ ERROR: Invalid backend '{backend}'. Must be one of: filebrowser, miniserve, qrcp, easy-sharing", err=True)
        raise typer.Exit(code=1)

    selected_port = port if port is not None else 8080
    if selected_port < 1 or selected_port > 65535:
        typer.echo(f"❌ ERROR: Invalid port '{selected_port}'. Port must be between 1 and 65535.", err=True)
        raise typer.Exit(code=1)

    path_obj = Path(path).expanduser().resolve()
    if not path_obj.exists():
        typer.echo(f"❌ ERROR: Path does not exist: {path}", err=True)
        raise typer.Exit(code=1)

    auth_supported = backend in ["filebrowser", "miniserve", "easy-sharing"]
    if no_auth and (username is not None or password is not None):
        typer.echo("❌ ERROR: --no-auth cannot be combined with --username or --password.", err=True)
        raise typer.Exit(code=1)
    if not no_auth and not auth_supported:
        typer.echo(f"❌ ERROR: Backend '{backend}' does not support authentication. Use --no-auth or choose another backend.", err=True)
        raise typer.Exit(code=1)

    auth_username: str | None = None
    auth_password: str | None = None
    if not no_auth:
        import getpass

        auth_username = username if username is not None else getpass.getuser()
        auth_password = password
        if auth_password is None:
            pwd_path = Path.home().joinpath("dotfiles/creds/passwords/quick_password")
            if pwd_path.exists():
                auth_password = pwd_path.read_text(encoding="utf-8").strip()
        if auth_password is None or auth_password == "":
            typer.echo("❌ ERROR: Password not provided. Pass --password or use --no-auth.", err=True)
            raise typer.Exit(code=1)

    if install_missing_dependencies:
        install_if_missing(which=backend, binary_name=None, verbose=True)
    if over_internet and install_missing_dependencies:
        install_if_missing(which="ngrok", binary_name=None, verbose=True)

    import stackops.scripts.python.helpers.helpers_network.address as helper
    res = helper.select_lan_ipv4(prefer_vpn=False)
    if res is None:
        typer.echo("❌ ERROR: Could not determine local LAN IPv4 address for share server.", err=True)
        raise typer.Exit(code=1)
    local_ip_v4 = res

    protocol = "http"
    display_host = local_ip_v4 if bind_address == "0.0.0.0" else bind_address
    display_with_flashy_style(msg=f"{protocol}://{display_host}:{selected_port}/", title="Local Network Share URL")

    pre_commands: list[str] = []
    if backend == "filebrowser":
        db_path = Path.home().joinpath(".config/filebrowser/filebrowser.db")
        db_path.parent.mkdir(parents=True, exist_ok=True)
        if auth_username is None or auth_password is None:
            server_command = shlex.join(["filebrowser", "--address", bind_address, "--port", str(selected_port), "--root", str(path_obj), "--database", str(db_path), "--noauth"])
        else:
            pre_commands.append(shlex.join(["filebrowser", "users", "add", auth_username, auth_password, "--database", str(db_path)]))
            server_command = shlex.join(["filebrowser", "--address", bind_address, "--port", str(selected_port), "--root", str(path_obj), "--database", str(db_path)])
    elif backend == "miniserve":
        server_args = ["miniserve", "--port", str(selected_port), "--interfaces", bind_address]
        if auth_username is not None and auth_password is not None:
            server_args.extend(["--auth", f"{auth_username}:{auth_password}"])
        server_args.extend(["--upload-files", "--mkdir", "--enable-tar", "--enable-tar-gz", "--enable-zip", "--qrcode", str(path_obj)])
        server_command = shlex.join(server_args)
    elif backend == "easy-sharing":
        server_args = ["easy-sharing", "--port", str(selected_port)]
        if auth_username is not None and auth_password is not None:
            server_args.extend(["--username", auth_username, "--password", auth_password])
        server_args.append(str(path_obj))
        server_command = shlex.join(server_args)
    elif backend == "qrcp":
        server_command = shlex.join(["qrcp", "--port", str(selected_port), "--bind", bind_address, str(path_obj)])
    else:
        typer.echo(f"❌ ERROR: Unknown backend '{backend}'", err=True)
        raise typer.Exit(code=1)

    if over_internet:
        command_lines = [
            *pre_commands,
            f"{server_command} &",
            "server_pid=$!",
            """trap 'kill "$server_pid" 2>/dev/null' INT TERM EXIT""",
            "sleep 1",
            """if ! kill -0 "$server_pid" 2>/dev/null; then""",
            """    wait "$server_pid"""",
            "    exit $?",
            "fi",
            shlex.join(["ngrok", "http", str(selected_port)]),
        ]
    else:
        command_lines = [*pre_commands, server_command]
    command = "\n".join(command_lines)

    from stackops.utils.code import exit_then_run_shell_script
    exit_then_run_shell_script(script=command, strict=False)
    # import subprocess
    # import time
    # server_process: subprocess.Popen[bytes]
    # server_process = subprocess.Popen(command, shell=True)
    # processes = [server_process]
    # if over_internet:
    #     ngrok_process = subprocess.Popen(f"ngrok http {port}", shell=True)
    #     processes.append(ngrok_process)
    #     time.sleep(3)
    #     try:
    #         import requests
    #         response = requests.get("http://localhost:4040/api/tunnels")
    #         data = response.json()
    #         public_url = data['tunnels'][0]['public_url']
    #         print(f"🌐 Ngrok tunnel ready: {public_url}")
    #     except Exception as e:
    #         print(f"Could not retrieve ngrok URL: {e}")
    
    # try:
    #     while True:
    #         print(f"Share server ({backend}) is running. Press Ctrl+C to stop.")
    #         time.sleep(2)
    # except KeyboardInterrupt:
    #     print("\nTerminating processes...")
    #     for p in processes:
    #         p.terminate()
    #         p.wait()


def get_share_file_app() -> typer.Typer:
    app = typer.Typer(name="share-file", help="Send or receive files using croc with relay server.")
    app.command(name="send", no_args_is_help=True, hidden=False, help="<s> send files from here.")(share_file_send)
    app.command(name="s", no_args_is_help=True, hidden=True, help="<s> send files from here.")(share_file_send)
    app.command(name="receive", no_args_is_help=True, hidden=False, help="<r> receive files to here.")(share_file_receive)
    app.command(name="r", no_args_is_help=True, hidden=True, help="<r> receive files to here.")(share_file_receive)
    return app

def main_with_parser() -> None:
    typer.run(web_file_explorer)


if __name__ == "__main__":
    pass
