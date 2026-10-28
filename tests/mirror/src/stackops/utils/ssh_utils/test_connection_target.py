from pathlib import Path

import pytest

from stackops.utils.ssh_utils.connection_target import SSHConnectionTarget, resolve_ssh_connection_profile


@pytest.mark.parametrize(
    ("destination", "hostname", "username", "port"),
    [
        ("workstation", "workstation", "local-user", 22),
        ("alex@workstation", "workstation", "alex", 22),
        ("workstation:2222", "workstation", "local-user", 2_222),
        ("alex@workstation:2222", "workstation", "alex", 2_222),
        ("2001:db8::10", "2001:db8::10", "local-user", 22),
        ("[2001:db8::10]:2222", "2001:db8::10", "local-user", 2_222),
        ("alex@[2001:db8::10]:2222", "2001:db8::10", "alex", 2_222),
    ],
)
def test_resolve_ssh_connection_profile_supports_every_ssh_destination_form(destination: str, hostname: str, username: str, port: int) -> None:
    def lookup_config(requested_hostname: str, _requested_username: str | None, _requested_port: int | None) -> dict[str, object]:
        return {"hostname": requested_hostname}

    profile = resolve_ssh_connection_profile(
        host=destination,
        username=None,
        hostname=None,
        ssh_key_path=None,
        port=22,
        local_username="local-user",
        ssh_config_lookup=lookup_config,
    )

    assert profile.target == SSHConnectionTarget(host=destination, hostname=hostname, username=username, port=port, ssh_key_path=None, proxy_command=None)


def test_resolve_ssh_connection_profile_uses_supported_ssh_config_options(tmp_path: Path) -> None:
    identity_file = tmp_path / "workstation-key"
    identity_file.touch()
    lookup_arguments: list[tuple[str, str | None, int | None]] = []

    def lookup_config(hostname: str, username: str | None, port: int | None) -> dict[str, object]:
        lookup_arguments.append((hostname, username, port))
        return {
            "hostname": "workstation.internal",
            "user": "remote-user",
            "port": "2200",
            "identityfile": [str(identity_file)],
            "proxyjump": "jump-user@gateway:2222",
        }

    profile = resolve_ssh_connection_profile(
        host="workstation",
        username=None,
        hostname=None,
        ssh_key_path=None,
        port=22,
        local_username="local-user",
        ssh_config_lookup=lookup_config,
    )

    assert lookup_arguments == [("workstation", None, None)]
    assert profile.target == SSHConnectionTarget(
        host="workstation",
        hostname="workstation.internal",
        username="remote-user",
        port=2_200,
        ssh_key_path=str(identity_file),
        proxy_command="ssh -T -l jump-user -p 2222 -W workstation.internal:2200 -- gateway",
    )
