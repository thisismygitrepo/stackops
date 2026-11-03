import socket
import subprocess
import time
import webbrowser
import json
from typing import Annotated, Final

import typer

from stackops.utils.ssh_utils.open_ssh_command import (
    OpenSSHCommandDestination,
    build_open_ssh_destination_arguments,
    parse_open_ssh_destination,
)


FORWARD_POLL_SECONDS: Final[float] = 0.05
FORWARD_CONNECT_TIMEOUT_SECONDS: Final[float] = 0.2
PROCESS_STOP_TIMEOUT_SECONDS: Final[float] = 5.0


def resolve_map_port_destination(destination: str, timeout: float) -> OpenSSHCommandDestination:
    parsed_destination = parse_open_ssh_destination(destination=destination)
    command = ("ssh", "-G", "-T", *build_open_ssh_destination_arguments(parsed_destination))
    subprocess.run(command, stdin=subprocess.DEVNULL, check=True, capture_output=True, encoding="utf-8", timeout=timeout)
    return parsed_destination


def build_map_port_command(
    ssh_destination: OpenSSHCommandDestination, remote_port: int, local_port: int
) -> tuple[str, ...]:
    for port_name, port in (("remote port", remote_port), ("local port", local_port)):
        if isinstance(port, bool) or not 1 <= port <= 65_535:
            raise ValueError(f"{port_name.capitalize()} must be between 1 and 65535, received {port}.")

    return (
        "ssh",
        "-N",
        "-T",
        "-o",
        "ExitOnForwardFailure=yes",
        "-o",
        "ClearAllForwardings=no",
        "-o",
        "ForkAfterAuthentication=no",
        "-o",
        "ControlMaster=no",
        "-S",
        "none",
        "-L",
        f"127.0.0.1:{local_port}:127.0.0.1:{remote_port}",
        *build_open_ssh_destination_arguments(ssh_destination),
    )


def ensure_local_port_available(local_port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as local_socket:
        try:
            local_socket.bind(("127.0.0.1", local_port))
        except OSError as error:
            raise ValueError(f"Local port {local_port} is unavailable: {error}.") from error


def wait_for_local_forward(ssh_process: subprocess.Popen[bytes], local_port: int, timeout: float) -> int | None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        exit_code = ssh_process.poll()
        if exit_code is not None:
            return exit_code
        try:
            with socket.create_connection(("127.0.0.1", local_port), timeout=FORWARD_CONNECT_TIMEOUT_SECONDS):
                time.sleep(FORWARD_POLL_SECONDS)
                return ssh_process.poll()
        except OSError:
            time.sleep(FORWARD_POLL_SECONDS)
    raise RuntimeError(f"SSH forwarding did not become ready within {timeout:g}s.")


def stop_ssh_process(ssh_process: subprocess.Popen[bytes]) -> None:
    if ssh_process.poll() is not None:
        return
    ssh_process.terminate()
    try:
        ssh_process.wait(timeout=PROCESS_STOP_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        ssh_process.kill()
        ssh_process.wait()


def map_port(
    destination: Annotated[str, typer.Argument(help="SSH config name or destination (host, user@host, or either form with an SSH port).")],
    remote_port: Annotated[int, typer.Argument(min=1, max=65_535, help="TCP port on the remote machine.")],
    local_port: Annotated[int | None, typer.Option("--local-port", "-l", min=1, max=65_535, help="Local TCP port; defaults to REMOTE_PORT.")] = None,
    open_browser: Annotated[bool, typer.Option("--open-browser", "-b", help="Open the mapped local HTTP address after the tunnel is ready.")] = False,
    background: Annotated[bool, typer.Option("--background", "-B", help="Keep the SSH tunnel running after this command exits.")] = False,
    output_json: Annotated[bool, typer.Option("--json", "-j", help="Print the ready local URL, PID, and log file as JSON.")] = False,
    timeout: Annotated[float, typer.Option("--timeout", "-T", min=1, help="Seconds to wait for SSH forwarding readiness.")] = 30.0,
) -> None:
    from stackops.utils.cli_utils.interaction import is_interactive, require_interactive
    from stackops.scripts.python.helpers.helpers_devops.network_service import start_service

    if open_browser:
        require_interactive("Opening the forwarded address in a browser; omit --open-browser")
    selected_local_port = remote_port if local_port is None else local_port
    try:
        ssh_destination = resolve_map_port_destination(destination=destination, timeout=timeout)
    except subprocess.CalledProcessError as error:
        error_detail = (
            error.stderr.strip() if isinstance(error.stderr, str) and error.stderr.strip() else f"OpenSSH exited with code {error.returncode}."
        )
        raise typer.BadParameter(error_detail, param_hint="DESTINATION") from error
    except (TypeError, ValueError) as error:
        raise typer.BadParameter(str(error), param_hint="DESTINATION") from error
    except (OSError, subprocess.TimeoutExpired) as error:
        typer.echo(f"Unable to start OpenSSH: {error}", err=True)
        raise typer.Exit(code=1) from error
    try:
        ensure_local_port_available(local_port=selected_local_port)
    except ValueError as error:
        raise typer.BadParameter(str(error), param_hint="LOCAL_PORT") from error

    command = build_map_port_command(
        ssh_destination=ssh_destination,
        remote_port=remote_port,
        local_port=selected_local_port,
    )
    if background or output_json or not is_interactive():
        command = ("ssh", "-o", "BatchMode=yes", "-o", f"ConnectTimeout={max(1, int(timeout))}", *command[1:])
    typer.echo(
        f"Mapping 127.0.0.1:{selected_local_port} to 127.0.0.1:{remote_port} through {destination}.", err=True,
    )
    service = None
    try:
        if background or output_json or not is_interactive():
            service = start_service("ssh-forward", list(command), background, None)
            ssh_process = service.process
        else:
            ssh_process = subprocess.Popen(command)
    except OSError as error:
        typer.echo(f"Unable to start OpenSSH: {error}", err=True)
        raise typer.Exit(code=1) from error

    try:
        readiness_exit_code = wait_for_local_forward(ssh_process=ssh_process, local_port=selected_local_port, timeout=timeout)
        if readiness_exit_code is not None:
            normalized_exit_code = 128 + abs(readiness_exit_code) if readiness_exit_code < 0 else readiness_exit_code or 1
            typer.echo(f"SSH forwarding exited before readiness; see {service.log_path if service is not None else 'the command output'}.", err=True)
            raise typer.Exit(code=normalized_exit_code)
        url = f"http://127.0.0.1:{selected_local_port}"
        if output_json:
            typer.echo(json.dumps({"status": "ready", "destination": destination, "remote_port": remote_port, "local_port": selected_local_port, "url": url, "pid": ssh_process.pid, "log_path": str(service.log_path) if service is not None else None, "background": background}))
        else:
            typer.echo(f"Ready: {url} (PID {ssh_process.pid})")
        if open_browser:
            if not webbrowser.open_new_tab(url):
                typer.echo("The tunnel is ready, but no browser accepted the local address.", err=True)
        if background:
            return
        exit_code = ssh_process.wait()
    except KeyboardInterrupt as error:
        stop_ssh_process(ssh_process=ssh_process)
        raise typer.Exit(code=130) from error
    except typer.Exit:
        stop_ssh_process(ssh_process=ssh_process)
        raise
    except Exception as error:
        stop_ssh_process(ssh_process=ssh_process)
        typer.echo(f"Unable to open the mapped address: {error}", err=True)
        raise typer.Exit(code=1) from error

    if exit_code != 0:
        normalized_exit_code = 128 + abs(exit_code) if exit_code < 0 else exit_code
        raise typer.Exit(code=normalized_exit_code)
