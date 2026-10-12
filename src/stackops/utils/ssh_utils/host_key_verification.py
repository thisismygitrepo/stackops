import base64
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import socket
import stat

import paramiko

from stackops.utils.ssh_utils.connection_target import SSHConnectionProfile


@dataclass(frozen=True, slots=True)
class HostKeyVerifiedConnection:
    client: paramiko.SSHClient
    proxy: paramiko.ProxyCommand | None


class ConfirmUnknownHostKey(paramiko.MissingHostKeyPolicy):
    def __init__(self, known_hosts_path: Path | None, hash_hostname: bool) -> None:
        self.known_hosts_path = known_hosts_path
        self.hash_hostname = hash_hostname

    def missing_host_key(self, client: paramiko.SSHClient, hostname: str, key: paramiko.PKey) -> None:
        digest = hashlib.sha256(key.asbytes()).digest()
        fingerprint = base64.b64encode(digest).decode("ascii").rstrip("=")
        persistence_prompt = (
            f"Trust this key and append it to {self.known_hosts_path}? [y/N]: "
            if self.known_hosts_path is not None
            else "Trust this key for this connection? [y/N]: "
        )
        response = input(
            f"Unknown SSH host key for {hostname}: {key.get_name()} SHA256:{fingerprint}\n"
            f"{persistence_prompt}"
        )
        if response.strip().casefold() not in {"y", "yes"}:
            raise paramiko.SSHException(f"Host key for {hostname} was not trusted.")

        client.get_host_keys().add(hostname, key.get_name(), key)
        if self.known_hosts_path is not None:
            stored_hostname = paramiko.HostKeys.hash_host(hostname) if self.hash_hostname else hostname
            _append_host_key(path=self.known_hosts_path, hostname=stored_hostname, key=key)


def connect_with_verified_host_key(
    profile: SSHConnectionProfile,
    password: str | None,
    passphrase: str | None,
    key_filename: str | list[str] | None,
    allow_agent: bool,
    look_for_keys: bool,
    compress: bool,
) -> HostKeyVerifiedConnection:
    target = profile.target
    client = paramiko.SSHClient()
    _configure_known_hosts(client=client, profile=profile)
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
            key_filename=key_filename,
            sock=connection_socket,
            compress=compress,
            allow_agent=allow_agent,
            look_for_keys=look_for_keys,
        )
    except Exception:
        client.close()
        if proxy is not None:
            proxy.close()
        if direct_socket is not None:
            direct_socket.close()
        raise
    return HostKeyVerifiedConnection(client=client, proxy=proxy)


def _configure_known_hosts(client: paramiko.SSHClient, profile: SSHConnectionProfile) -> None:
    for configured_path in profile.global_known_hosts_files:
        path = _resolve_configured_path(value=configured_path)
        if path is not None and path.is_file():
            client.load_system_host_keys(str(path))
    writable_path: Path | None = None
    for configured_path in profile.user_known_hosts_files:
        path = _resolve_configured_path(value=configured_path)
        if path is None:
            continue
        if writable_path is None:
            writable_path = path
        if path.is_file():
            client.load_host_keys(str(path))
    client.set_missing_host_key_policy(
        ConfirmUnknownHostKey(known_hosts_path=writable_path, hash_hostname=profile.hash_known_hosts)
    )


def _resolve_configured_path(value: str) -> Path | None:
    if value.casefold() == "none":
        return None
    return Path(os.path.expandvars(value)).expanduser()


@contextmanager
def _exclusive_file_lock(file_descriptor: int) -> Generator[None]:
    if os.name == "nt":
        import msvcrt

        os.lseek(file_descriptor, 0, os.SEEK_SET)
        msvcrt.locking(file_descriptor, msvcrt.LK_LOCK, 1)
        try:
            yield
        finally:
            os.lseek(file_descriptor, 0, os.SEEK_SET)
            msvcrt.locking(file_descriptor, msvcrt.LK_UNLCK, 1)
        return

    import fcntl

    fcntl.flock(file_descriptor, fcntl.LOCK_EX)
    try:
        yield
    finally:
        fcntl.flock(file_descriptor, fcntl.LOCK_UN)


def _append_host_key(path: Path, hostname: str, key: paramiko.PKey) -> None:
    directory_was_missing = not path.parent.exists()
    file_was_missing = not path.exists()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    default_ssh_directory = Path.home().joinpath(".ssh")
    if os.name != "nt" and (directory_was_missing or path.parent == default_ssh_directory):
        path.parent.chmod(0o700)

    entry = f"{hostname} {key.get_name()} {key.get_base64()}\n".encode("ascii")
    file_descriptor = os.open(path, os.O_APPEND | os.O_CREAT | os.O_RDWR, 0o600)
    try:
        with _exclusive_file_lock(file_descriptor=file_descriptor):
            file_size = os.fstat(file_descriptor).st_size
            separator = b""
            if file_size > 0:
                os.lseek(file_descriptor, -1, os.SEEK_END)
                if os.read(file_descriptor, 1) != b"\n":
                    separator = b"\n"
            appended_entry = separator + entry
            written_bytes = os.write(file_descriptor, appended_entry)
            if written_bytes != len(appended_entry):
                raise OSError(
                    f"Only {written_bytes} of {len(appended_entry)} known-host bytes were written to {path}."
                )
        if file_was_missing and os.name != "nt" and stat.S_ISREG(os.fstat(file_descriptor).st_mode):
            os.fchmod(file_descriptor, 0o600)
    finally:
        os.close(file_descriptor)
