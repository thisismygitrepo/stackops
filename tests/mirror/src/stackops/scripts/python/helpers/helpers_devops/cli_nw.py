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


def test_vscode_share_share_local_keeps_extra_options_before_directory(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str] = {}

    monkeypatch.setattr(
        "stackops.scripts.python.helpers.helpers_devops.cli_nw_vscode_share.resolve_share_local_folder",
        lambda directory: "/tmp/my workspace",
    )
    monkeypatch.setattr(
        "stackops.scripts.python.helpers.helpers_devops.cli_nw_vscode_share.print_serve_web_urls",
        lambda cmd, folder_path: captured.update({"urls_cmd": cmd, "folder_path": folder_path}),
    )
    monkeypatch.setattr(
        "stackops.utils.code.print_code",
        lambda code, lexer, desc, subtitle="": captured.update({"printed_cmd": code, "lexer": lexer, "desc": desc}),
    )
    monkeypatch.setattr(
        "stackops.utils.code.exit_then_run_shell_script",
        lambda script, strict=False: captured.update({"executed_cmd": script, "strict": str(strict)}),
    )

    result = CliRunner().invoke(
        cli_nw.get_app(),
        ["vscode-share", "share-local", "--extra-args=--port=9001"],
    )

    assert result.exit_code == 0
    executed_cmd = captured["executed_cmd"]
    assert "--without-connection-token --port=9001" in executed_cmd
    assert executed_cmd.index("--port=9001") < executed_cmd.index("'/tmp/my workspace'")
    assert captured["folder_path"] == "/tmp/my workspace"
