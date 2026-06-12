"""Wifi connect

Linux requirements:
- sudo apt-get install network-manager

Windows requirements:
- Run as Administrator for netsh commands

Usage examples:
  python wifi_conn.py                     # Use default SSID from config
  python wifi_conn.py -n HomeWiFi         # Use specific configured network
  python wifi_conn.py -m                  # Manual network selection
  python wifi_conn.py -l                  # List available networks only

"""

import getpass
import json
import platform
from importlib import import_module
from typing import Protocol, cast

from rich.prompt import Prompt

from stackops.scripts.python.helpers.helpers_network.wifi_conn_platforms.common import (
    WifiNetwork,
    console,
    render_networks_table,
)


class WifiPlatformModule(Protocol):
    def get_available_networks(self) -> list[WifiNetwork]: ...

    def connect(self, name: str, ssid: str) -> None: ...

    def connect_to_new_network(self, ssid: str, password: str) -> None: ...

    def display_available_networks(self) -> None: ...

    def get_current_wifi_name(self) -> str: ...

    def create_new_connection(self, name: str, ssid: str, password: str) -> None: ...


def _get_platform_module() -> WifiPlatformModule:
    module_name: str
    system_name = platform.system()
    if system_name == "Linux":
        module_name = "stackops.scripts.python.helpers.helpers_network.wifi_conn_platforms.linux"
    elif system_name == "Windows":
        module_name = "stackops.scripts.python.helpers.helpers_network.wifi_conn_platforms.windows"
    elif system_name == "Darwin":
        module_name = "stackops.scripts.python.helpers.helpers_network.wifi_conn_platforms.darwin"
    else:
        module_name = "stackops.scripts.python.helpers.helpers_network.wifi_conn_platforms.unsupported"
    return cast(WifiPlatformModule, import_module(module_name))


def get_available_networks() -> list[WifiNetwork]:
    return _get_platform_module().get_available_networks()


def display_and_select_network() -> WifiNetwork | None:
    console.print("\n[blue]📡 Scanning for available WiFi networks...[/blue]")

    networks = get_available_networks()

    if not networks:
        console.print("[red]❌ No networks found or error occurred[/red]")
        return None

    render_networks_table(networks, title="Available WiFi Networks")

    try:
        choice = Prompt.ask("\n[blue]Select network number (or 'q' to quit)[/blue]", default="q")

        if choice.lower() == "q":
            return None

        index = int(choice) - 1
        if 0 <= index < len(networks):
            return networks[index]
        console.print(f"[red]❌ Invalid selection. Please choose 1-{len(networks)}[/red]")
        return None

    except ValueError:
        console.print("[red]❌ Invalid input. Please enter a number.[/red]")
        return None


def connect(name: str, ssid: str) -> None:
    _get_platform_module().connect(name, ssid)


def connect_to_new_network(ssid: str, password: str) -> None:
    _get_platform_module().connect_to_new_network(ssid, password)


def display_available_networks() -> None:
    _get_platform_module().display_available_networks()


def try_config_connection(config_ssid: str) -> bool:
    try:
        from stackops.secrets.paths import SECRETS_DOFILE
        from stackops.secrets.models import Login
        from stackops.secrets.search import search_logins
        secrets = search_logins(path=SECRETS_DOFILE, login_name=config_ssid, tags=("wifi",), keys=("ssid", "password"))
        if not secrets:
            expected_entry: Login = {
                "name": config_ssid,
                "tags": ["wifi"],
                "secrets": [
                    {
                        "name": "credentials",
                        "tags": [],
                        "scopes": [],
                        "keyValues": {
                            "ssid": config_ssid,
                            "password": "<wifi-password>",
                        },
                    }
                ],
            }
            console.print(f"[yellow]⚠️ No configuration found for SSID '{config_ssid}'[/yellow]")
            console.print(f"Expected {SECRETS_DOFILE} to contain a login entry shaped like:", markup=False)
            console.print(json.dumps(expected_entry, indent=2), markup=False)
            return False
        if len(secrets) > 1:
            console.print(f"[yellow]⚠️ Multiple configurations found for SSID '{config_ssid}', using the first one[/yellow]")
            return False
        ssid = secrets[0]["secrets"][0]["keyValues"]["ssid"]
        if not isinstance(ssid, str):
            raise TypeError(f"Secret value at {config_ssid}.ssid must be a string.")
        password = secrets[0]["secrets"][0]["keyValues"]["password"]
        if not isinstance(password, str):
            raise TypeError(f"Secret value at {config_ssid}.password must be a string.")

        console.print(f"[green]✅ Found configuration for {config_ssid}[/green]")
        connect_to_new_network(ssid, password)
        return True

    except Exception as error:
        console.print(f"[red]❌ Error reading configuration: {error}[/red]")
        return False


def manual_network_selection() -> bool:
    network = display_and_select_network()

    if not network:
        return False

    ssid = network["ssid"]
    console.print(f"\n[blue]Selected network: {ssid}[/blue]")

    password = getpass.getpass(f"Enter password for '{ssid}': ")

    if not password:
        console.print("[red]❌ Password cannot be empty[/red]")
        return False

    try:
        connect_to_new_network(ssid, password)
        return True
    except Exception:
        return False


def get_current_wifi_name() -> str:
    return _get_platform_module().get_current_wifi_name()


def create_new_connection(name: str, ssid: str, password: str) -> None:
    _get_platform_module().create_new_connection(name, ssid, password)
