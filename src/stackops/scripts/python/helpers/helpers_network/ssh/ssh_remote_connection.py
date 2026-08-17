import base64
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
import getpass
import hashlib
import os
from pathlib import Path
from typing import cast

import paramiko

from stackops.utils.ssh_utils.connection_target import SSHConnectionTarget, resolve_ssh_connection_target
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


class ConfirmUnknownHostKey(paramiko.MissingHostKeyPolicy):
    def __init__(self, known_hosts_path: Path) -> None:
        self.known_hosts_path = known_hosts_path

    def missing_host_key(self, client: paramiko.SSHClient, hostname: str, key: paramiko.PKey) -> None:
        digest = hashlib.sha256(key.asbytes()).digest()
        fingerprint = base64.b64encode(digest).decode("ascii").rstrip("=")
        response = input(
            f"Unknown SSH host key for {hostname}: {key.get_name()} SHA256:{fingerprint}\n"
            "Trust this key and add it to known_hosts? [y/N]: "
        )
        if response.strip().casefold() not in {"y", "yes"}:
            raise paramiko.SSHException(f"Host key for {hostname} was not trusted.")

        directory_was_missing = not self.known_hosts_path.parent.exists()
        self.known_hosts_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if directory_was_missing and os.name != "nt":
            self.known_hosts_path.parent.chmod(0o700)
        client.get_host_keys().add(hostname, key.get_name(), key)
        client.save_host_keys(str(self.known_hosts_path))
        if os.name != "nt":
            self.known_hosts_path.chmod(0o600)


@contextmanager
def open_remote_connection(remote_target: str, password: str | None) -> Iterator[ConnectedRemote]:
    parsed_destination = parse_open_ssh_destination(destination=remote_target)
    target = resolve_ssh_connection_target(
        host=remote_target,
        username=parsed_destination.username,
        hostname=None,
        ssh_key_path=None,
        port=parsed_destination.port if parsed_destination.port is not None else 22,
        local_username=getpass.getuser(),
        ssh_config_lookup=lookup_open_ssh_config,
    )
    known_hosts_path = Path.home().joinpath(".ssh", "known_hosts")
    try:
        connection = _connect_once(target=target, known_hosts_path=known_hosts_path, password=None, automatic_authentication=True)
    except paramiko.SSHException as error:
        is_authentication_failure = isinstance(error, (paramiko.AuthenticationException, paramiko.PasswordRequiredException)) or str(error) == (
            "No authentication methods available"
        )
        if not is_authentication_failure:
            raise
        selected_password = password
        if selected_password is None:
            selected_password = getpass.getpass(f"Password for {target.username}@{target.hostname}: ")
        connection = _connect_once(
            target=target,
            known_hosts_path=known_hosts_path,
            password=selected_password,
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
    stdout_bytes = cast(bytes, stdout.read())
    stderr_bytes = cast(bytes, stderr.read())
    return_code = stdout.channel.recv_exit_status()
    return RemoteCommandResult(
        return_code=return_code,
        stdout=stdout_bytes.decode("utf-8", errors="replace"),
        stderr=stderr_bytes.decode("utf-8", errors="replace"),
    )


def _connect_once(
    target: SSHConnectionTarget,
    known_hosts_path: Path,
    password: str | None,
    automatic_authentication: bool,
) -> ConnectedRemote:
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    for system_known_hosts in (Path("/etc/ssh/ssh_known_hosts"), Path("/etc/ssh/ssh_known_hosts2")):
        if system_known_hosts.is_file():
            client.load_system_host_keys(str(system_known_hosts))
    if known_hosts_path.is_file():
        client.load_host_keys(str(known_hosts_path))
    client.set_missing_host_key_policy(ConfirmUnknownHostKey(known_hosts_path=known_hosts_path))
    proxy = paramiko.ProxyCommand(target.proxy_command) if target.proxy_command is not None else None
    try:
        client.connect(
            hostname=target.hostname,
            username=target.username,
            password=password,
            port=target.port,
            key_filename=target.ssh_key_path if automatic_authentication else None,
            sock=proxy,
            allow_agent=automatic_authentication,
            look_for_keys=automatic_authentication,
        )
    except Exception:
        client.close()
        if proxy is not None:
            proxy.close()
        raise
    return ConnectedRemote(client=client, target=target, proxy=proxy)


def encode_powershell_command(script: str) -> str:
    encoded_script = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    return f"powershell.exe -NoLogo -NoProfile -NonInteractive -EncodedCommand {encoded_script}"
