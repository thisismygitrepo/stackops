import getpass
import os
import subprocess
import webbrowser
from typing import Annotated

import typer

from stackops.utils.ssh_utils.connection_target import SSHConnectionTarget, resolve_ssh_connection_target
from stackops.utils.ssh_utils.open_ssh_config import lookup_open_ssh_config


def resolve_map_port_destination(destination: str) -> SSHConnectionTarget:
    return resolve_ssh_connection_target(
        host=destination,
        username=None,
        hostname=None,
        ssh_key_path=None,
        port=22,
        local_username=getpass.getuser(),
        ssh_config_lookup=lookup_open_ssh_config,
    )


def build_map_port_command(ssh_destination: SSHConnectionTarget, remote_port: int, local_port: int) -> tuple[str, ...]:
    for port_name, port in (("remote port", remote_port), ("local port", local_port)):
        if isinstance(port, bool) or not 1 <= port <= 65_535:
            raise ValueError(f"{port_name.capitalize()} must be between 1 and 65535, received {port}.")

    command = [
        "ssh",
        "-F",
        os.devnull,
        "-N",
        "-T",
        "-o",
        "ExitOnForwardFailure=yes",
        "-o",
        "ForkAfterAuthentication=no",
        "-o",
        "ControlMaster=no",
        "-S",
        "none",
        "-L",
        f"127.0.0.1:{local_port}:127.0.0.1:{remote_port}",
    ]
    if ssh_destination.ssh_key_path is not None:
        command.extend(("-i", ssh_destination.ssh_key_path))
    if ssh_destination.proxy_command is not None:
        command.extend(("-o", f"ProxyCommand={ssh_destination.proxy_command}"))
    command.extend(("-l", ssh_destination.username, "-p", str(ssh_destination.port)))
    command.extend(("--", ssh_destination.hostname))
    return tuple(command)


def map_port(
    destination: Annotated[str, typer.Argument(help="SSH config name or destination (host, user@host, or either form with an SSH port).")],
    remote_port: Annotated[int, typer.Argument(min=1, max=65_535, help="TCP port on the remote machine.")],
    local_port: Annotated[int | None, typer.Option("--local-port", "-l", min=1, max=65_535, help="Local TCP port; defaults to REMOTE_PORT.")] = None,
    open_browser: Annotated[bool, typer.Option("--open-browser", "-b", help="Open the mapped local address in the default browser.")] = False,
) -> None:
    selected_local_port = remote_port if local_port is None else local_port
    try:
        ssh_destination = resolve_map_port_destination(destination=destination)
    except subprocess.CalledProcessError as error:
        error_detail = (
            error.stderr.strip() if isinstance(error.stderr, str) and error.stderr.strip() else f"OpenSSH exited with code {error.returncode}."
        )
        raise typer.BadParameter(error_detail, param_hint="DESTINATION") from error
    except (TypeError, ValueError) as error:
        raise typer.BadParameter(str(error), param_hint="DESTINATION") from error
    except OSError as error:
        typer.echo(f"Unable to start OpenSSH: {error}", err=True)
        raise typer.Exit(code=1) from error
    command = build_map_port_command(ssh_destination=ssh_destination, remote_port=remote_port, local_port=selected_local_port)
    typer.echo(f"Mapping 127.0.0.1:{selected_local_port} to 127.0.0.1:{remote_port} through {destination}. Press Ctrl-C to stop.")
    try:
        ssh_process = subprocess.Popen(command)
    except OSError as error:
        typer.echo(f"Unable to start OpenSSH: {error}", err=True)
        raise typer.Exit(code=1) from error
    if open_browser:
        webbrowser.open_new_tab(f"http://127.0.0.1:{selected_local_port}")
    exit_code = ssh_process.wait()
    if exit_code != 0:
        raise typer.Exit(code=exit_code)
