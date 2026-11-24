from dataclasses import dataclass
from typing import TypedDict

from stackops.scripts.python.helpers.helpers_webui.network_constants import WIFI_STRONGEST_DBM, WIFI_WEAKEST_DBM


@dataclass(frozen=True, slots=True)
class WifiProblem:
    status: int
    message: str


# How strong the connection is. `percent` is always there; the rest is what the system adds to it, empty or None where it says nothing.
class WifiSignal(TypedDict):
    percent: int
    dbm: int | None
    noise: int | None
    channel: str
    standard: str
    rate: str


# `name_hidden` is a Mac that is connected and will not say to what: macOS gives the name only to apps with location access.
class WifiCurrent(TypedDict):
    connected: bool
    name: str
    name_hidden: bool
    security: str


class NearbyNetwork(TypedDict):
    name: str
    percent: int
    security: str
    in_use: bool


# What one system says about its Wi-Fi. `signal_later` is a system whose signal takes seconds to read, so the page asks for it apart.
# `remembered` are the networks the system itself has joined before; `problem` is why nothing could be read.
class PlatformWifi(TypedDict):
    adapter: str
    radio_on: bool
    current: WifiCurrent
    signal: WifiSignal | None
    signal_later: bool
    remembered: list[str]
    problem: str


NOT_CONNECTED: WifiCurrent = {"connected": False, "name": "", "name_hidden": False, "security": ""}


def percent_of(dbm: int) -> int:
    share = (dbm - WIFI_WEAKEST_DBM) / (WIFI_STRONGEST_DBM - WIFI_WEAKEST_DBM)
    return round(min(max(share, 0.0), 1.0) * 100)
