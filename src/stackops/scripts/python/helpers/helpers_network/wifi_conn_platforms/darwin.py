import re
import subprocess
from typing import Final, Never

from stackops.scripts.python.helpers.helpers_network.wifi_conn_platforms.common import (
    WifiNetwork,
    console,
    deduplicate_networks,
    render_networks_table,
    run_text_command,
)

_AIRPORT_BINARY: Final[str] = "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport"
_AIRPORT_SCAN_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^(?P<ssid>.+?)\s+(?P<bssid>(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2})\s+(?P<rssi>-?\d+)\s+"
)


def _parse_airport_scan_output(stdout: str) -> list[WifiNetwork]:
    networks: list[WifiNetwork] = []
    for line_number, raw_line in enumerate(stdout.splitlines()):
        if line_number == 0 or raw_line.strip() == "":
            continue
        match = _AIRPORT_SCAN_PATTERN.match(raw_line.rstrip())
        if match is None:
            continue
        ssid = match.group("ssid").strip()
        if ssid == "":
            continue
        networks.append({"ssid": ssid, "signal": f"{match.group('rssi')} dBm"})
    return networks


def _raise_unsupported(operation: str) -> Never:
    error = RuntimeError(f"WiFi {operation} is not implemented for macOS")
    console.print(f"[red]❌ {error}[/red]")
    raise error


def get_available_networks() -> list[WifiNetwork]:
    networks: list[WifiNetwork] = []

    try:
        result = run_text_command([_AIRPORT_BINARY, "-s"], check=True)
        networks = _parse_airport_scan_output(result.stdout)
    except subprocess.CalledProcessError as error:
        console.print(f"[red]❌ Error scanning networks: {error}[/red]")
    except Exception as error:
        console.print(f"[red]❌ Unexpected error: {error}[/red]")

    return deduplicate_networks(networks)


def connect(name: str, ssid: str) -> None:
    console.print(f"\n[blue]🌐 Connecting to network: {name} (SSID: {ssid})[/blue]")
    _raise_unsupported("connections")


def connect_to_new_network(ssid: str, password: str) -> None:
    del password
    console.print(f"\n[blue]🌐 Connecting to network: {ssid} (SSID: {ssid})[/blue]")
    _raise_unsupported("connections")


def display_available_networks() -> None:
    console.print("\n[blue]📡 Scanning for available networks...[/blue]")
    networks = get_available_networks()
    if len(networks) == 0:
        console.print("[yellow]⚠️  No visible WiFi networks were reported[/yellow]")
        return
    render_networks_table(networks, title="Available WiFi Networks")
    console.print("[green]✅ Network scan completed![/green]\n")


def get_current_wifi_name() -> str:
    console.print("\n[blue]🔍 Checking current WiFi connection...[/blue]")

    try:
        result = run_text_command([_AIRPORT_BINARY, "-I"], check=True)
        for raw_line in result.stdout.splitlines():
            line = raw_line.strip()
            if not line.startswith("SSID:"):
                continue
            _, raw_wifi_name = line.split(":", maxsplit=1)
            wifi_name = raw_wifi_name.strip()
            if wifi_name != "":
                console.print(f"[green]✅ Connected to: {wifi_name}[/green]\n")
                return wifi_name
        console.print("[yellow]⚠️  Not connected to WiFi[/yellow]\n")
        return "Not connected to WiFi"
    except subprocess.CalledProcessError:
        console.print("[yellow]⚠️  Not connected to WiFi or unable to detect[/yellow]\n")
        return "Not connected to WiFi"
    except Exception as error:
        console.print(f"[red]❌ Error: {error}[/red]\n")
        return "Error detecting WiFi"


def create_new_connection(name: str, ssid: str, password: str) -> None:
    del name
    del ssid
    del password
    _raise_unsupported("profile creation")