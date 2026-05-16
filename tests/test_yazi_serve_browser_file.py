import pytest

from stackops.scripts.python.helpers.helpers_network import address as address_helper
from stackops.settings.yazi.scripts import serve_browser_file


def test_get_lan_addresses_uses_selected_lan_ipv4(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[bool] = []

    def fake_select_lan_ipv4(*, prefer_vpn: bool) -> str:
        calls.append(prefer_vpn)
        return "192.168.0.10"

    monkeypatch.setattr(address_helper, "select_lan_ipv4", fake_select_lan_ipv4)

    assert serve_browser_file.get_lan_addresses() == ["192.168.0.10"]
    assert calls == [False]


def test_get_lan_addresses_returns_empty_when_no_lan_ipv4(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(address_helper, "select_lan_ipv4", lambda *, prefer_vpn: None)

    assert serve_browser_file.get_lan_addresses() == []
