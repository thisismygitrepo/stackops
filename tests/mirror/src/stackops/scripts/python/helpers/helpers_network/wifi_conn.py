import subprocess

import pytest

from stackops.scripts.python.helpers.helpers_network import wifi_conn
from stackops.scripts.python.helpers.helpers_network.wifi_conn_platforms import linux as linux_wifi


def test_parse_linux_wifi_scan_output_preserves_escaped_colons() -> None:
    parsed_networks = linux_wifi._parse_linux_wifi_scan_output("""Cafe\\:Guest:78
MyPhoneHotSpot:92
""")

    assert parsed_networks == [
        {"ssid": "Cafe:Guest", "signal": "78%"},
        {"ssid": "MyPhoneHotSpot", "signal": "92%"},
    ]


def test_get_available_networks_recovers_unmanaged_linux_device(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wifi_conn.platform, "system", lambda: "Linux")

    status_outputs = iter(
        [
            "wlp195s0:wifi:unmanaged\n",
            "wlp195s0:wifi:unmanaged\n",
            "wlp195s0:wifi:disconnected\n",
        ]
    )
    observed_commands: list[list[str]] = []

    def fake_run(command: list[str], *args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        del args
        observed_commands.append(command)
        match command:
            case ["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device", "status"]:
                return subprocess.CompletedProcess(args=command, returncode=0, stdout=next(status_outputs), stderr="")
            case ["nmcli", "radio", "wifi"]:
                return subprocess.CompletedProcess(args=command, returncode=0, stdout="enabled\n", stderr="")
            case ["nmcli", "device", "set", "wlp195s0", "managed", "yes"]:
                return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")
            case ["nmcli", "device", "wifi", "rescan"]:
                return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")
            case ["nmcli", "-t", "-f", "SSID,SIGNAL", "device", "wifi", "list", "ifname", "wlp195s0"]:
                return subprocess.CompletedProcess(args=command, returncode=0, stdout="MyPhoneHotSpot:92\nCafe\\:Guest:74\n", stderr="")
            case _:
                raise AssertionError(f"Unexpected command: {command}")

    monkeypatch.setattr(linux_wifi.subprocess, "run", fake_run)

    available_networks = wifi_conn.get_available_networks()

    assert available_networks == [
        {"ssid": "MyPhoneHotSpot", "signal": "92%"},
        {"ssid": "Cafe:Guest", "signal": "74%"},
    ]
    assert ["nmcli", "device", "set", "wlp195s0", "managed", "yes"] in observed_commands


def test_connect_to_new_network_uses_argument_list_for_linux(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wifi_conn.platform, "system", lambda: "Linux")

    status_outputs = iter(
        [
            "wlp195s0:wifi:disconnected\n",
            "wlp195s0:wifi:disconnected\n",
        ]
    )
    observed_calls: list[tuple[list[str], object | None]] = []

    def fake_run(command: list[str], *args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        del args
        observed_calls.append((command, kwargs.get("shell")))
        match command:
            case ["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device", "status"]:
                return subprocess.CompletedProcess(args=command, returncode=0, stdout=next(status_outputs), stderr="")
            case ["nmcli", "radio", "wifi"]:
                return subprocess.CompletedProcess(args=command, returncode=0, stdout="enabled\n", stderr="")
            case ["nmcli", "device", "wifi", "connect", "MyPhoneHotSpot", "password", "super-secret", "ifname", "wlp195s0"]:
                return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")
            case _:
                raise AssertionError(f"Unexpected command: {command}")

    monkeypatch.setattr(linux_wifi.subprocess, "run", fake_run)

    wifi_conn.connect_to_new_network("MyPhoneHotSpot", "super-secret")

    assert observed_calls[-1] == (
        ["nmcli", "device", "wifi", "connect", "MyPhoneHotSpot", "password", "super-secret", "ifname", "wlp195s0"],
        None,
    )
