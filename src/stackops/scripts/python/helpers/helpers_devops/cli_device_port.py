import subprocess
from typing import Annotated

import typer

from stackops.utils.ssh_utils.connection_target import parse_ssh_destination


def build_map_port_command(destination: str, remote_port: int, local_port: int) -> tuple[str, ...]:
    for port_name, port in (("remote port", remote_port), ("local port", local_port)):
        if isinstance(port, bool) or not 1 <= port <= 65_535:
            raise ValueError(f"{port_name.capitalize()} must be between 1 and 65535, received {port}.")

    ssh_destination = parse_ssh_destination(destination=destination)
    command = [
        "ssh",
        "-N",
        "-T",
        "-o",
        "ExitOnForwardFailure=yes",
        "-L",
        f"127.0.0.1:{local_port}:127.0.0.1:{remote_port}",
    ]
    if ssh_destination.username is not None:
        command.extend(("-l", ssh_destination.username))
    if ssh_destination.port is not None:
        command.extend(("-p", str(ssh_destination.port)))
    command.extend(("--", ssh_destination.hostname))
    return tuple(command)


def map_port(
    destination: Annotated[
        str,
        typer.Argument(help="SSH config name or destination (host, user@host, or either form with an SSH port)."),
    ],
    remote_port: Annotated[int, typer.Argument(min=1, max=65_535, help="TCP port on the remote machine.")],
    local_port: Annotated[
        int | None,
        typer.Option("--local-port", "-l", min=1, max=65_535, help="Local TCP port; defaults to REMOTE_PORT."),
    ] = None,
) -> None:
    selected_local_port = remote_port if local_port is None else local_port
    command = build_map_port_command(destination=destination, remote_port=remote_port, local_port=selected_local_port)
    typer.echo(
        f"Mapping 127.0.0.1:{selected_local_port} to 127.0.0.1:{remote_port} through {destination}. Press Ctrl-C to stop."
    )
    completed_process = subprocess.run(command, check=False)
    if completed_process.returncode != 0:
        raise typer.Exit(code=completed_process.returncode)


def register_commands(device_app: typer.Typer) -> None:
    device_app.command(
        name="map-port",
        help="🔀 <m> Map a remote TCP port to local loopback over SSH",
        no_args_is_help=True,
    )(map_port)
    device_app.command(
        name="m",
        help="Map a remote TCP port to local loopback over SSH",
        hidden=True,
        no_args_is_help=True,
    )(map_port)
