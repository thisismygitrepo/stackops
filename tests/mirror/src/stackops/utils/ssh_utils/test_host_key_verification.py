from collections.abc import Generator, Mapping
from dataclasses import dataclass
from pathlib import Path
import socket
import threading

import paramiko
import pytest

from stackops.utils.ssh_utils.connection_target import SSHConnectionProfile, resolve_ssh_connection_profile
from stackops.utils.ssh_utils.host_key_verification import connect_with_verified_host_key


@dataclass(frozen=True, slots=True)
class LoopbackServer:
    port: int
    host_key: paramiko.PKey
    authenticated_usernames: list[str]


class _PasswordServer(paramiko.ServerInterface):
    def __init__(self, authenticated_usernames: list[str]) -> None:
        self.authenticated_usernames = authenticated_usernames

    def get_allowed_auths(self, username: str) -> str:
        return "password"

    def check_auth_password(self, username: str, password: str) -> int:
        self.authenticated_usernames.append(username)
        return paramiko.AUTH_SUCCESSFUL


@pytest.fixture
def loopback_server() -> Generator[LoopbackServer]:
    host_key = paramiko.ECDSAKey.generate()
    authenticated_usernames: list[str] = []
    listener = socket.create_server(("127.0.0.1", 0))
    transports: list[paramiko.Transport] = []

    def serve() -> None:
        while True:
            try:
                connection, _address = listener.accept()
            except OSError:
                return
            transport = paramiko.Transport(connection)
            transport.add_server_key(host_key)
            transport.start_server(server=_PasswordServer(authenticated_usernames=authenticated_usernames))
            transports.append(transport)

    threading.Thread(target=serve, daemon=True).start()
    yield LoopbackServer(port=listener.getsockname()[1], host_key=host_key, authenticated_usernames=authenticated_usernames)
    listener.close()
    for transport in transports:
        transport.close()


def _profile(port: int, known_hosts_file: Path, host_key_alias: str | None) -> SSHConnectionProfile:
    def lookup(_hostname: str, _username: str | None, _port: int | None) -> Mapping[str, object]:
        options: dict[str, object] = {"hostname": "127.0.0.1", "port": str(port), "user": "tester", "userknownhostsfile": [str(known_hosts_file)]}
        if host_key_alias is not None:
            options["hostkeyalias"] = host_key_alias
        return options

    return resolve_ssh_connection_profile(
        host="pinned-machine", username=None, hostname=None, ssh_key_path=None, port=22, local_username="tester", ssh_config_lookup=lookup
    )


def _connect(profile: SSHConnectionProfile) -> None:
    connection = connect_with_verified_host_key(
        profile=profile, password="password", passphrase=None, key_filename=None, allow_agent=False, look_for_keys=False, compress=False
    )
    connection.client.close()


def _refuse_prompt(prompt: str) -> str:
    raise AssertionError(f"""Unexpected host-key prompt: {prompt}""")


@pytest.mark.parametrize("answer", ["n", ""])
def test_unknown_host_key_rejected_before_authentication(
    loopback_server: LoopbackServer, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, answer: str
) -> None:
    known_hosts_file = tmp_path / "known_hosts"
    monkeypatch.setattr("builtins.input", lambda _prompt: answer)
    with pytest.raises(paramiko.SSHException, match="was not trusted"):
        _connect(profile=_profile(port=loopback_server.port, known_hosts_file=known_hosts_file, host_key_alias=None))
    assert loopback_server.authenticated_usernames == []
    assert not known_hosts_file.exists()


@pytest.mark.parametrize(
    ("host_key_alias", "known_hosts_name"), [(None, "[127.0.0.1]:{port}"), ("pinned-alias", "pinned-alias")]
)
def test_host_key_pinned_in_configured_file_connects_without_prompt(
    loopback_server: LoopbackServer, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, host_key_alias: str | None, known_hosts_name: str
) -> None:
    host_key = loopback_server.host_key
    known_hosts_file = tmp_path / "custom_known_hosts"
    known_hosts_file.write_text(
        f"""{known_hosts_name.format(port=loopback_server.port)} {host_key.get_name()} {host_key.get_base64()}\n""", encoding="utf-8"
    )
    monkeypatch.setattr("builtins.input", _refuse_prompt)
    _connect(profile=_profile(port=loopback_server.port, known_hosts_file=known_hosts_file, host_key_alias=host_key_alias))
    assert loopback_server.authenticated_usernames == ["tester"]


def test_mismatched_host_key_rejected_before_authentication(
    loopback_server: LoopbackServer, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    impostor_key = paramiko.ECDSAKey.generate()
    known_hosts_file = tmp_path / "known_hosts"
    known_hosts_file.write_text(f"""[127.0.0.1]:{loopback_server.port} {impostor_key.get_name()} {impostor_key.get_base64()}\n""", encoding="utf-8")
    monkeypatch.setattr("builtins.input", _refuse_prompt)
    with pytest.raises(paramiko.BadHostKeyException):
        _connect(profile=_profile(port=loopback_server.port, known_hosts_file=known_hosts_file, host_key_alias=None))
    assert loopback_server.authenticated_usernames == []
