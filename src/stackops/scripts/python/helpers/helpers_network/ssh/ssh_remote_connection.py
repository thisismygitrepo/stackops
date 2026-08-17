import base64
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
import getpass
import socket

import paramiko

from stackops.scripts.python.helpers.helpers_network.ssh.ssh_known_hosts import configure_known_hosts
from stackops.utils.ssh_utils.connection_target import SSHConnectionProfile, SSHConnectionTarget, resolve_ssh_connection_profile
from stackops.utils.ssh_utils.open_ssh_command import parse_open_ssh_destination
from stackops.utils.ssh_utils.open_ssh_config import lookup_open_ssh_config


@dataclass(frozen=True, slots=True)
class ConnectedRemote:
    client: paramiko.SSHClient
    target: SSHConnectionTarget
    proxy: paramiko.ProxyCommand | None


@dataclass(frozen=True, slots=True)
class RemoteCommandResult:
    return_code: int
    stdout: str
    stderr: str


@contextmanager
def open_remote_connection(remote_target: str, password: str | None) -> Generator[ConnectedRemote]:
    parsed_destination = parse_open_ssh_destination(destination=remote_target)
    profile = resolve_ssh_connection_profile(
        host=remote_target,
        username=parsed_destination.username,
        hostname=None,
        ssh_key_path=None,
        port=parsed_destination.port if parsed_destination.port is not None else 22,
        local_username=getpass.getuser(),
        ssh_config_lookup=lookup_open_ssh_config,
    )
    target = profile.target
    connection: ConnectedRemote | None = None
    try:
        connection = _connect_once(
            profile=profile,
            password=None,
            passphrase=None,
            automatic_authentication=True,
        )
    except paramiko.PasswordRequiredException:
        selected_passphrase = getpass.getpass(f"Passphrase for the SSH key used by {target.username}@{target.hostname}: ")
        try:
            connection = _connect_once(
                profile=profile,
                password=None,
                passphrase=selected_passphrase,
                automatic_authentication=True,
            )
        except paramiko.SSHException as error:
            if not _is_account_authentication_failure(error=error):
                raise
    except paramiko.SSHException as error:
        if not _is_account_authentication_failure(error=error):
            raise

    if connection is None:
        selected_password = password
        if selected_password is None:
            selected_password = getpass.getpass(f"Password for {target.username}@{target.hostname}: ")
        connection = _connect_once(
            profile=profile,
            password=selected_password,
            passphrase=None,
            automatic_authentication=False,
        )

    try:
        yield connection
    finally:
        connection.client.close()
        if connection.proxy is not None:
            connection.proxy.close()


def run_remote_command(connection: ConnectedRemote, command: str) -> RemoteCommandResult:
    stdin, stdout, stderr = connection.client.exec_command(command=command)
    stdin.close()
    stdout_bytes = stdout.read()
    stderr_bytes = stderr.read()
    return_code = stdout.channel.recv_exit_status()
    return RemoteCommandResult(
        return_code=return_code,
        stdout=stdout_bytes.decode("utf-8", errors="replace"),
        stderr=stderr_bytes.decode("utf-8", errors="replace"),
    )


def _connect_once(
    profile: SSHConnectionProfile,
    password: str | None,
    passphrase: str | None,
    automatic_authentication: bool,
) -> ConnectedRemote:
    target = profile.target
    client = paramiko.SSHClient()
    configure_known_hosts(client=client, profile=profile)
    proxy = paramiko.ProxyCommand(target.proxy_command) if target.proxy_command is not None else None
    direct_socket: socket.socket | None = None
    connection_socket: paramiko.ProxyCommand | socket.socket | None = proxy
    connection_hostname = target.hostname
    connection_port = target.port
    if profile.host_key_alias is not None:
        connection_hostname = profile.host_key_alias
        connection_port = 22
        if connection_socket is None:
            direct_socket = socket.create_connection((target.hostname, target.port))
            connection_socket = direct_socket
    try:
        client.connect(
            hostname=connection_hostname,
            username=target.username,
            password=password,
            passphrase=passphrase,
            port=connection_port,
            key_filename=list(profile.identity_files) if automatic_authentication and profile.identity_files else None,  # type: ignore[arg-type]
            sock=connection_socket,
            allow_agent=automatic_authentication and not profile.identities_only,
            look_for_keys=automatic_authentication and not profile.identities_only,
        )
    except Exception:
        client.close()
        if proxy is not None:
            proxy.close()
        if direct_socket is not None:
            direct_socket.close()
        raise
    return ConnectedRemote(client=client, target=target, proxy=proxy)


def _is_account_authentication_failure(error: paramiko.SSHException) -> bool:
    if isinstance(error, paramiko.PasswordRequiredException):
        return False
    return isinstance(error, paramiko.AuthenticationException) or str(error) == "No authentication methods available"


def encode_powershell_command(script: str) -> str:
    encoded_script = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    return f"powershell.exe -NoLogo -NoProfile -NonInteractive -EncodedCommand {encoded_script}"
