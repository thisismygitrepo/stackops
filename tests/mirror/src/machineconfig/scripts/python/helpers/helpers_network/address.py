import socket
import subprocess
import sys
import types

import pytest

import machineconfig.scripts.python.helpers.helpers_network.address as subject

_INSTALLER_MODULE = "machineconfig.utils.installer_utils.installer_cli"



def test_get_public_ip_address_installs_cli_and_parses_json(monkeypatch: pytest.MonkeyPatch) -> None:
    installer_calls: list[tuple[str, str | None, bool]] = []

    def fake_install_if_missing(*, which: str, binary_name: str | None, verbose: bool) -> None:
        installer_calls.append((which, binary_name, verbose))

    def fake_run(
        args: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        encoding: str,
    ) -> types.SimpleNamespace:
        assert args == ["ipinfo", "myip", "--json"]
        assert check is True
        assert capture_output is True
        assert text is True
        assert encoding == "utf-8"
        return types.SimpleNamespace(
            stdout=(
                '{"ip":"1.1.1.1","hostname":"","city":"","region":"","country":"","country_name":"",'
                '"country_flag":{},"country_flag_url":"","country_currency":{},"continent":{},'
                '"loc":"","org":"","postal":"","timezone":""}'
            )
        )

    installer_module = types.ModuleType(_INSTALLER_MODULE)
    setattr(installer_module, "install_if_missing", fake_install_if_missing)
    monkeypatch.setitem(sys.modules, _INSTALLER_MODULE, installer_module)
    monkeypatch.setattr(subprocess, "run", fake_run)

    result = subject.get_public_ip_address()

    assert installer_calls == [("ipinfo", None, True)]
    assert result["ip"] == "1.1.1.1"



def test_get_all_ipv4_addresses_keeps_only_ipv4(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_psutil = types.ModuleType("psutil")
    setattr(
        fake_psutil,
        "net_if_addrs",
        lambda: {
            "eth0": [
                types.SimpleNamespace(family=socket.AF_INET, address="192.168.0.5"),
                types.SimpleNamespace(family=socket.AF_INET6, address="fe80::1"),
            ],
            "lo": [types.SimpleNamespace(family=socket.AF_INET, address="127.0.0.1")],
        },
    )
    monkeypatch.setitem(sys.modules, "psutil", fake_psutil)

    result = subject.get_all_ipv4_addresses()

    assert result == [("eth0", "192.168.0.5"), ("lo", "127.0.0.1")]



def test_select_lan_ipv4_prefers_physical_private_interface(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_psutil = types.ModuleType("psutil")
    setattr(
        fake_psutil,
        "net_if_stats",
        lambda: {
            "eth0": types.SimpleNamespace(isup=True, speed=1000),
            "docker0": types.SimpleNamespace(isup=True, speed=0),
            "tailscale0": types.SimpleNamespace(isup=True, speed=0),
        },
    )
    setattr(
        fake_psutil,
        "net_if_addrs",
        lambda: {
            "eth0": [types.SimpleNamespace(family=socket.AF_INET, address="192.168.50.8", broadcast="192.168.50.255")],
            "docker0": [types.SimpleNamespace(family=socket.AF_INET, address="172.17.0.1", broadcast="172.17.255.255")],
            "tailscale0": [types.SimpleNamespace(family=socket.AF_INET, address="100.64.0.4", broadcast=None)],
        },
    )
    monkeypatch.setitem(sys.modules, "psutil", fake_psutil)

    result = subject.select_lan_ipv4(prefer_vpn=False)

    assert result == "192.168.50.8"



def test_select_lan_ipv4_can_return_vpn_when_requested(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_psutil = types.ModuleType("psutil")
    setattr(
        fake_psutil,
        "net_if_stats",
        lambda: {"tailscale0": types.SimpleNamespace(isup=True, speed=0)},
    )
    setattr(
        fake_psutil,
        "net_if_addrs",
        lambda: {"tailscale0": [types.SimpleNamespace(family=socket.AF_INET, address="100.64.1.5", broadcast=None)]},
    )
    monkeypatch.setitem(sys.modules, "psutil", fake_psutil)

    result = subject.select_lan_ipv4(prefer_vpn=True)

    assert result == "100.64.1.5"
