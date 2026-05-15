import pytest
from typer.testing import CliRunner

from stackops.scripts.python.helpers.helpers_devops import cli_nw
from stackops.scripts.python.helpers.helpers_network import address as address_helper


def test_show_address_prints_mac_addresses(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_print_json(*, data: object) -> None:
        del data

    public_ip_info: address_helper.PublicIpInfo = {
        "ip": "112.213.241.103",
        "hostname": "",
        "city": "",
        "region": "",
        "country": "",
        "country_name": "",
        "country_flag": {"emoji": "", "unicode": ""},
        "country_flag_url": "",
        "country_currency": {"code": "", "symbol": ""},
        "continent": {"code": "", "name": ""},
        "loc": "",
        "org": "",
        "postal": "",
        "timezone": "",
    }

    monkeypatch.setattr("rich.print_json", fake_print_json)
    monkeypatch.setattr(address_helper, "get_public_ip_address", lambda: public_ip_info)
    monkeypatch.setattr(
        address_helper,
        "get_all_interface_ipv4_addresses",
        lambda: [
            address_helper.InterfaceIPv4Address(interface="lo0", ipv4_address="127.0.0.1", mac_address=None),
            address_helper.InterfaceIPv4Address(interface="en1", ipv4_address="192.168.0.203", mac_address="aa:bb:cc:dd:ee:ff"),
        ],
    )
    monkeypatch.setattr(
        address_helper,
        "select_lan_interface_ipv4",
        lambda *, prefer_vpn: address_helper.InterfaceIPv4Address(
            interface="en1",
            ipv4_address="192.168.0.203",
            mac_address="aa:bb:cc:dd:ee:ff",
        ),
    )

    result = CliRunner().invoke(cli_nw.get_app(), ["show-address"])

    assert result.exit_code == 0
    assert "MAC Address" in result.stdout
    assert "Public IP" in result.stdout
    assert "aa:bb:cc:dd:ee:ff" in result.stdout
    assert "LAN IPv4: 192.168.0.203" in result.stdout
    assert "LAN MAC: aa:bb:cc:dd:ee:ff" in result.stdout
