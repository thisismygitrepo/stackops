import subprocess
from typing import Final, TypedDict

from rich.console import Console
from rich.table import Table

console: Final[Console] = Console()


class WifiNetwork(TypedDict):
    ssid: str
    signal: str


def run_text_command(command: list[str], *, check: bool) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=check)


def deduplicate_networks(networks: list[WifiNetwork]) -> list[WifiNetwork]:
    seen: set[str] = set()
    unique_networks: list[WifiNetwork] = []
    for network in networks:
        ssid = network["ssid"]
        if ssid == "" or ssid in seen:
            continue
        seen.add(ssid)
        unique_networks.append(network)
    return unique_networks


def render_networks_table(networks: list[WifiNetwork], *, title: str) -> None:
    table = Table(title=title)
    table.add_column("Index", style="cyan", no_wrap=True)
    table.add_column("SSID", style="green")
    table.add_column("Signal Strength", style="yellow")

    for index, network in enumerate(networks, start=1):
        table.add_row(str(index), network["ssid"], network["signal"])

    console.print(table)