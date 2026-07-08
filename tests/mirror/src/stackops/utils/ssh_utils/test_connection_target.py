from pathlib import Path

import pytest

from stackops.utils.ssh_utils.connection_target import SSHConnectionTarget, resolve_ssh_connection_target
from stackops.utils.ssh_utils.open_ssh_config import parse_open_ssh_config


def test_alias_uses_effective_open_ssh_hostname_and_remote_username() -> None:
    config_options = parse_open_ssh_config("""hostname oda.internal
user remote-user
port 22
""")

    target = resolve_ssh_connection_target(
        host="oda",
        username=None,
        hostname=None,
        ssh_key_path=None,
        port=22,
        local_username="local-user",
        ssh_config_lookup=lambda _hostname, _username, _port: config_options,
    )

    assert target == SSHConnectionTarget(host="oda", hostname="oda.internal", username="remote-user", port=22, ssh_key_path=None, proxy_command=None)


def test_alias_without_configured_user_uses_local_username() -> None:
    config_options = parse_open_ssh_config("""hostname oda.internal
port 22
""")

    target = resolve_ssh_connection_target(
        host="oda",
        username=None,
        hostname=None,
        ssh_key_path=None,
        port=22,
        local_username="local-user",
        ssh_config_lookup=lambda _hostname, _username, _port: config_options,
    )

    assert target.username == "local-user"


def test_alias_uses_effective_connection_options(tmp_path: Path) -> None:
    identity_file = tmp_path / "oda-key"
    identity_file.touch()
    config_options = parse_open_ssh_config(f"""hostname oda.internal
user remote-user
port 2200
identityfile {identity_file}
identityfile ~/.ssh/default
proxycommand ssh gateway -W %h:%p
""")

    target = resolve_ssh_connection_target(
        host="oda",
        username=None,
        hostname=None,
        ssh_key_path=None,
        port=22,
        local_username="local-user",
        ssh_config_lookup=lambda _hostname, _username, _port: config_options,
    )

    assert target.hostname == "oda.internal"
    assert target.username == "remote-user"
    assert target.port == 2200
    assert target.ssh_key_path == str(identity_file)
    assert target.proxy_command == "ssh gateway -W oda.internal:2200"


def test_bare_hostname_without_specific_config_uses_open_ssh_defaults() -> None:
    target = resolve_ssh_connection_target(
        host="server.internal",
        username=None,
        hostname=None,
        ssh_key_path=None,
        port=22,
        local_username="local-user",
        ssh_config_lookup=lambda hostname, _username, _port: {"hostname": hostname},
    )

    assert target == SSHConnectionTarget(
        host="server.internal", hostname="server.internal", username="local-user", port=22, ssh_key_path=None, proxy_command=None
    )


def test_inline_user_and_port_are_used_for_lookup_and_override_config() -> None:
    lookup_arguments: list[tuple[str, str | None, int | None]] = []

    def lookup(hostname: str, username: str | None, port: int | None) -> dict[str, object]:
        lookup_arguments.append((hostname, username, port))
        return {"hostname": "oda.internal", "user": "configured-user", "port": "2200"}

    target = resolve_ssh_connection_target(
        host="inline-user@oda:2222",
        username="argument-user",
        hostname=None,
        ssh_key_path=None,
        port=22,
        local_username="local-user",
        ssh_config_lookup=lookup,
    )

    assert lookup_arguments == [("oda", "inline-user", 2222)]
    assert target.hostname == "oda.internal"
    assert target.username == "inline-user"
    assert target.port == 2222


def test_explicit_connection_arguments_override_optional_config_values() -> None:
    config_options: dict[str, object] = {"hostname": "oda.internal", "user": "configured-user", "identityfile": ["/configured/key"]}

    target = resolve_ssh_connection_target(
        host="oda",
        username="argument-user",
        hostname=None,
        ssh_key_path="/explicit/key",
        port=22,
        local_username="local-user",
        ssh_config_lookup=lambda _hostname, _username, _port: config_options,
    )

    assert target.username == "argument-user"
    assert target.ssh_key_path == "/explicit/key"


def test_proxy_jump_is_converted_to_open_ssh_stdio_proxy() -> None:
    config_options = parse_open_ssh_config("""hostname oda.internal
user remote-user
port 2200
proxyjump jump-user@gateway:2222
""")

    target = resolve_ssh_connection_target(
        host="oda",
        username=None,
        hostname=None,
        ssh_key_path=None,
        port=22,
        local_username="local-user",
        ssh_config_lookup=lambda _hostname, _username, _port: config_options,
    )

    assert target.proxy_command == "ssh -T -l jump-user -p 2222 -W oda.internal:2200 -- gateway"


@pytest.mark.parametrize("port", ["0", "65536", "not-a-port"])
def test_invalid_configured_port_is_rejected(port: str) -> None:
    config_options = {"hostname": "oda.internal", "port": port}

    with pytest.raises(ValueError, match="SSH port"):
        resolve_ssh_connection_target(
            host="oda",
            username=None,
            hostname=None,
            ssh_key_path=None,
            port=22,
            local_username="local-user",
            ssh_config_lookup=lambda _hostname, _username, _port: config_options,
        )
