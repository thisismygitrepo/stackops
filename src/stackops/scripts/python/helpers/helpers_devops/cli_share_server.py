from pathlib import Path
from typing import Annotated, Literal

import typer
from typer._completion_classes import completion_init
from typer.completion import install_callback, show_callback

from stackops.scripts.python.helpers.helpers_devops.cli_share_file import share_file_receive, share_file_send


def web_file_explorer(
    path: Annotated[str, typer.Argument(help="Path to the file or directory to share")],
    port: Annotated[int | None, typer.Option("--port", "-p", help="Port to run the share server on (default: any free port)")] = None,
    username: Annotated[str | None, typer.Option("--username", "-u", help="Username for share access (default: current user)")] = None,
    no_auth: Annotated[bool, typer.Option("--no-auth", "-n", help="Disable authentication for share access")] = False,
    password: Annotated[str | None, typer.Option("--password", "-w", help="Password for share access (default: configured quick password)")] = None,
    host: Annotated[str, typer.Option("--host", "-H", help="Address to bind the server to")] = "0.0.0.0",
    over_internet: Annotated[bool, typer.Option("--over-internet", "-i", help="Expose the share server over the internet using ngrok")] = False,
    backend: Annotated[Literal["filebrowser", "miniserve", "qrcp", "easy-sharing"], typer.Option("--backend", "-b", help="Backend that serves the files")] = "filebrowser",
    install_missing_dependencies: Annotated[bool, typer.Option("--install-dep", "-D", help="Install missing dependencies", show_default=False)] = False,
    background: Annotated[bool, typer.Option("--background", "-B", help="Keep the server running after this command exits.")] = False,
    output_json: Annotated[bool, typer.Option("--json", "-j", help="Print ready URLs, process IDs, and log files as JSON.")] = False,
    timeout: Annotated[float, typer.Option("--timeout", "-T", min=1, help="Seconds to wait for each service to become ready.")] = 30.0,
    password_file: Annotated[Path | None, typer.Option("--password-file", "-f", help="Read access password from a file; '-' reads stdin.")] = None,
    password_env: Annotated[str | None, typer.Option("--password-env", "-E", help="Environment variable containing the access password.")] = None,
) -> None:
    import shutil
    import subprocess
    from stackops.secrets.paths import SECRETS_DOFILE
    from stackops.secrets.readers import read_quick_password
    from stackops.scripts.python.helpers.helpers_devops.network_service import find_free_port, install_service_dependency, run_network_service
    from stackops.utils.cli_utils.secret_input import read_secret_input

    if port is None:
        selected_port = find_free_port(host=host, preferred_port=0)
    elif port < 1 or port > 65535:
        typer.echo(f"❌ ERROR: Invalid port '{port}'. Port must be between 1 and 65535.", err=True)
        raise typer.Exit(code=1)
    else:
        selected_port = port

    path_obj = Path(path).expanduser().resolve()
    if not path_obj.exists():
        typer.echo(f"❌ ERROR: Path does not exist: {path}", err=True)
        raise typer.Exit(code=1)

    auth_supported = backend in ["filebrowser", "miniserve", "easy-sharing"]
    if no_auth and (username is not None or password is not None or password_file is not None or password_env is not None):
        typer.echo("❌ ERROR: --no-auth cannot be combined with --username or --password.", err=True)
        raise typer.Exit(code=1)
    if not no_auth and not auth_supported:
        typer.echo(f"❌ ERROR: Backend '{backend}' does not support authentication. Use --no-auth or choose another backend.", err=True)
        raise typer.Exit(code=1)

    auth_username: str | None = None
    auth_password: str | None = None
    password_source = "value passed with --password"
    if password_file is not None or password_env is not None:
        password = read_secret_input(value=password, file=password_file, env=password_env, prompt="Share access password")
        password_source = f"read from --password-file {password_file}" if password_file is not None else f"read from environment variable {password_env} (--password-env)"
    if not no_auth:
        import getpass

        auth_username = username if username is not None else getpass.getuser()
        auth_password = password
        if auth_password is None:
            try:
                auth_password = read_quick_password()
            except Exception:
                auth_password = None
            password_source = f"quick password, login 'quickPassword' in {SECRETS_DOFILE}; override with --password, --password-file or --password-env"
        if auth_password is None or auth_password == "":
            typer.echo("❌ ERROR: Password not provided. Pass --password or use --no-auth.", err=True)
            raise typer.Exit(code=1)
        typer.echo(f"Username: {auth_username} ({'passed with --username' if username is not None else 'current OS user; override with --username'})", err=True)
        typer.echo(f"Password: {password_source}", err=True)
    else:
        typer.echo("Auth: none (--no-auth), anyone who can reach the port has access", err=True)

    if install_missing_dependencies:
        install_service_dependency(backend)
    if over_internet and install_missing_dependencies:
        install_service_dependency("ngrok")

    import stackops.utils.network.address as helper
    res = helper.select_lan_ipv4(prefer_vpn=False)
    if res is None:
        typer.echo("❌ ERROR: Could not determine local LAN IPv4 address for share server.", err=True)
        raise typer.Exit(code=1)
    local_ip_v4 = res

    protocol = "http"
    display_host = local_ip_v4 if host == "0.0.0.0" else host
    setup_steps: list[tuple[str, list[str]]] = []
    setup_secret: str | None = auth_password
    state_directory: Path | None = None
    match backend:
        case "filebrowser":
            import secrets
            import tempfile

            services_directory = Path.home().joinpath(".cache/stackops/network-services")
            services_directory.mkdir(parents=True, exist_ok=True)
            # A database per run: filebrowser refuses to add a user to a missing database or one that already has that user, and holds a lock on it while serving.
            state_directory = Path(tempfile.mkdtemp(prefix="filebrowser-db-", dir=services_directory))
            database = str(state_directory.joinpath("filebrowser.db"))
            if auth_username is None or auth_password is None:
                auth_method, account_name, setup_secret = "noauth", "anonymous", secrets.token_urlsafe(24)
            else:
                auth_method, account_name, setup_secret = "json", auth_username, auth_password
            setup_steps.append(("filebrowser config init", ["filebrowser", "config", "init", "--database", database, "--auth.method", auth_method, "--minimumPasswordLength", "1"]))
            setup_steps.append(("filebrowser users add", ["filebrowser", "users", "add", account_name, setup_secret, "--database", database]))
            server_args = ["filebrowser", "--address", host, "--port", str(selected_port), "--root", str(path_obj), "--database", database]
        case "miniserve":
            server_args = ["miniserve", "--port", str(selected_port), "--interfaces", host]
            if auth_username is not None and auth_password is not None:
                server_args.extend(["--auth", f"{auth_username}:{auth_password}"])
            server_args.extend(["--upload-files", "--mkdir", "--enable-tar", "--enable-tar-gz", "--enable-zip", "--qrcode", str(path_obj)])
        case "easy-sharing":
            server_args = ["easy-sharing", "--port", str(selected_port)]
            if auth_username is not None and auth_password is not None:
                server_args.extend(["--username", auth_username, "--password", auth_password])
            server_args.append(str(path_obj))
        case "qrcp":
            interfaces = helper.get_all_interface_ipv4_addresses()
            interface = "any" if host == "0.0.0.0" else next((entry.interface for entry in interfaces if entry.ipv4_address == host), None)
            if interface is None:
                raise typer.BadParameter("The qrcp bind address must match a local network interface.")
            server_args = ["qrcp", "--port", str(selected_port), "--interface", interface, "--fqdn", display_host, *(["--keep-alive"] if background else []), str(path_obj)]

    try:
        for step, command in setup_steps:
            try:
                result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=timeout)
            except FileNotFoundError:
                typer.echo(f"❌ ERROR: '{command[0]}' is not installed or not on PATH. Pass --install-dep to install it.", err=True)
                raise typer.Exit(code=1) from None
            except subprocess.TimeoutExpired:
                typer.echo(f"❌ ERROR: '{step}' did not finish within {timeout:g} seconds.", err=True)
                raise typer.Exit(code=1) from None
            if result.returncode != 0:
                output = "\n".join(line for line in f"{result.stdout}\n{result.stderr}".splitlines() if line.strip() != "")
                if setup_secret is not None:
                    output = output.replace(setup_secret, "<password>")
                typer.echo(f"❌ ERROR: '{step}' failed with exit code {result.returncode}:\n{output}", err=True)
                raise typer.Exit(code=1)
        run_network_service(name=backend, arguments=server_args, host=host, port=selected_port, url=f"{protocol}://{display_host}:{selected_port}/", over_internet=over_internet, background=background, output_json=output_json, timeout=timeout, url_from_log=backend == "qrcp")
    finally:
        if state_directory is not None and not background:
            shutil.rmtree(state_directory, ignore_errors=True)


def get_share_file_app() -> typer.Typer:
    completion_init()
    app = typer.Typer(
        name="share-file", help="Send or receive files using croc with relay server.",
        add_completion=False,
        context_settings={"help_option_names": ["-h", "--help"]},
    )

    @app.callback()
    def _completion_options(
        _install_completion: Annotated[
            bool, typer.Option("--install-completion", "-I", callback=install_callback, expose_value=False, help="Install completion for the current shell.")
        ] = False,
        _show_completion: Annotated[
            bool, typer.Option("--show-completion", "-S", callback=show_callback, expose_value=False, help="Show completion for the current shell, to copy it or customize the installation.")
        ] = False,
    ) -> None:
        pass

    app.command(name="send", no_args_is_help=True, hidden=False, help="📤 <s> send files from here.")(share_file_send)
    app.command(name="s", no_args_is_help=True, hidden=True, help="<s> send files from here.")(share_file_send)
    app.command(name="receive", no_args_is_help=True, hidden=False, help="📥 <r> receive files to here.")(share_file_receive)
    app.command(name="r", no_args_is_help=True, hidden=True, help="<r> receive files to here.")(share_file_receive)
    return app

def main_with_parser() -> None:
    app = typer.Typer(add_completion=False, context_settings={"help_option_names": ["-h", "--help"]})
    app.command()(web_file_explorer)
    app()


if __name__ == "__main__":
    pass
