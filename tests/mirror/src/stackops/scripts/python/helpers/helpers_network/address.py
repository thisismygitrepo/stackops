import socket
from types import SimpleNamespace

import pytest

from stackops.scripts.python.helpers.helpers_network import address


def test_get_all_interface_ipv4_addresses_includes_mac_addresses(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(address, "_interface_link_families", lambda: {999})
    monkeypatch.setattr(
        "psutil.net_if_addrs",
        lambda: {
            "en1": [
                SimpleNamespace(family=999, address="AA-BB-CC-DD-EE-FF"),
                SimpleNamespace(family=socket.AF_INET, address="192.168.0.203"),
            ],
            "lo0": [
                SimpleNamespace(family=999, address="00:00:00:00:00:00"),
                SimpleNamespace(family=socket.AF_INET, address="127.0.0.1"),
            ],
        },
    )

    addresses = address.get_all_interface_ipv4_addresses()

    assert addresses == [
        address.InterfaceIPv4Address(interface="en1", ipv4_address="192.168.0.203", mac_address="aa:bb:cc:dd:ee:ff"),
        address.InterfaceIPv4Address(interface="lo0", ipv4_address="127.0.0.1", mac_address=None),
    ]
