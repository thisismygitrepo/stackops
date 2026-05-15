import platform
from typing import Never

from stackops.scripts.python.helpers.helpers_network.wifi_conn_platforms.common import WifiNetwork, console


def _raise_unsupported(operation: str) -> Never:
    system_name = platform.system() or "Unknown"
    error = RuntimeError(f"WiFi {operation} is not supported on {system_name}")
    console.print(f"[red]❌ {error}[/red]")
    raise error


def get_available_networks() -> list[WifiNetwork]:
    system_name = platform.system() or "Unknown"
    console.print(f"[yellow]⚠️  WiFi helpers are not supported on {system_name}[/yellow]")
    return []


def connect(name: str, ssid: str) -> None:
    del name
    del ssid
    _raise_unsupported("connections")


def connect_to_new_network(ssid: str, password: str) -> None:
    del ssid
    del password
    _raise_unsupported("connections")


def display_available_networks() -> None:
    system_name = platform.system() or "Unknown"
    console.print(f"[yellow]⚠️  WiFi helpers are not supported on {system_name}[/yellow]")


def get_current_wifi_name() -> str:
    system_name = platform.system() or "Unknown"
    console.print(f"[yellow]⚠️  WiFi helpers are not supported on {system_name}[/yellow]\n")
    return "System not supported"


def create_new_connection(name: str, ssid: str, password: str) -> None:
    del name
    del ssid
    del password
    _raise_unsupported("profile creation")