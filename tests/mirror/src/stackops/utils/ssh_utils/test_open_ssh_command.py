import pytest

from stackops.utils.ssh_utils.open_ssh_command import (
    OpenSSHCommandDestination,
    build_open_ssh_destination_arguments,
    parse_open_ssh_destination,
)


@pytest.mark.parametrize(
    ("destination", "hostname", "username", "port"),
    [
        ("workstation", "workstation", None, None),
        ("alex@workstation", "workstation", "alex", None),
        ("workstation:2222", "workstation", None, 2_222),
        ("alex@workstation:2222", "workstation", "alex", 2_222),
        ("2001:db8::10", "2001:db8::10", None, None),
        ("[2001:db8::10]:2222", "2001:db8::10", None, 2_222),
        ("alex@[2001:db8::10]:2222", "2001:db8::10", "alex", 2_222),
    ],
)
def test_parse_open_ssh_destination_supports_every_ssh_destination_form(
    destination: str, hostname: str, username: str | None, port: int | None
) -> None:
    assert parse_open_ssh_destination(destination=destination) == OpenSSHCommandDestination(hostname=hostname, username=username, port=port)


@pytest.mark.parametrize("destination", ["", "bad@", "@host", "host:0", "host:65536", "host:port", "[::1", "[::1]x", "bad host", "alex@bad host"])
def test_parse_open_ssh_destination_rejects_malformed_destinations(destination: str) -> None:
    with pytest.raises(ValueError):
        parse_open_ssh_destination(destination=destination)


def test_build_open_ssh_destination_arguments_terminates_options_before_hostname() -> None:
    assert build_open_ssh_destination_arguments(OpenSSHCommandDestination(hostname="-oProxyCommand=evil", username=None, port=None)) == (
        "--",
        "-oProxyCommand=evil",
    )
    assert build_open_ssh_destination_arguments(OpenSSHCommandDestination(hostname="workstation", username="alex", port=2_222)) == (
        "-l",
        "alex",
        "-p",
        "2222",
        "--",
        "workstation",
    )
