import json
import re
from typing import cast

from stackops.scripts.python.helpers.helpers_webui.network_constants import WIFI_COMMAND_SECONDS, WIFI_SIGNAL_SECONDS
from stackops.scripts.python.helpers.helpers_webui.network_system import read_tool
from stackops.scripts.python.helpers.helpers_webui.network_wifi_model import NOT_CONNECTED, PlatformWifi, WifiCurrent, WifiSignal, percent_of

HIDDEN_NAME = "<redacted>"
SECURITY_WORDS = {"NONE": "Open", "WPA_PSK": "WPA", "WPA2_PSK": "WPA2", "WPA3_SAE": "WPA3", "WPA2_ENTERPRISE": "WPA2 Enterprise", "WPA3_ENTERPRISE": "WPA3 Enterprise"}
DBM_PATTERN = re.compile(r"(-?\d+)\s*dBm")


def find_adapter() -> str:
    ports = read_tool(command=["networksetup", "-listallhardwareports"], seconds=WIFI_COMMAND_SECONDS) or ""
    found = re.search(r"Hardware Port: (?:Wi-Fi|AirPort)\nDevice: (\S+)", ports)
    return found.group(1) if found is not None else ""


# Everything here comes from tools that only read and never scan: a scan is what makes macOS ask for location access. The price is that
# the network's name comes back hidden on a current macOS, and the list of nearby networks is not asked for at all.
def read_state() -> PlatformWifi:
    adapter = find_adapter()
    state: PlatformWifi = {"adapter": adapter, "radio_on": False, "current": NOT_CONNECTED, "signal": None, "signal_later": False, "remembered": [], "problem": ""}
    if adapter == "":
        return {**state, "problem": "This Mac has no Wi-Fi adapter."}
    power = read_tool(command=["networksetup", "-getairportpower", adapter], seconds=WIFI_COMMAND_SECONDS) or ""
    radio_on = power.strip().endswith("On")
    summary = read_tool(command=["ipconfig", "getsummary", adapter], seconds=WIFI_COMMAND_SECONDS) or ""
    facts = {key.strip(): value.strip() for key, _, value in (line.partition(" : ") for line in summary.splitlines()) if value != ""}
    current: WifiCurrent = NOT_CONNECTED
    if radio_on and facts.get("LinkStatusActive") == "TRUE" and "SSID" in facts:
        hidden = facts["SSID"] == HIDDEN_NAME
        security = facts.get("Security", "")
        current = {"connected": True, "name": "" if hidden else facts["SSID"], "name_hidden": hidden, "security": SECURITY_WORDS.get(security, security.replace("_", " "))}
    listed = read_tool(command=["networksetup", "-listpreferredwirelessnetworks", adapter], seconds=WIFI_COMMAND_SECONDS) or ""
    remembered = [line.strip() for line in listed.splitlines()[1:] if line.strip() != ""]
    return {**state, "radio_on": radio_on, "current": current, "signal_later": current["connected"], "remembered": remembered}


# The system report is the one place macOS gives the signal without administrator rights. It takes about three seconds.
def read_signal() -> WifiSignal | None:
    adapter = find_adapter()
    report = read_tool(command=["system_profiler", "SPAirPortDataType", "-json"], seconds=WIFI_SIGNAL_SECONDS)
    if adapter == "" or report is None:
        return None
    try:
        loaded = cast(dict[str, list[dict[str, list[dict[str, object]]]]], json.loads(report))
        interfaces = loaded["SPAirPortDataType"][0]["spairport_airport_interfaces"]
    except (ValueError, KeyError, IndexError, TypeError):
        return None
    for interface in interfaces:
        details = interface.get("spairport_current_network_information")
        if interface.get("_name") != adapter or not isinstance(details, dict):
            continue
        facts = cast(dict[str, object], details)
        levels = [int(level) for level in DBM_PATTERN.findall(str(facts.get("spairport_signal_noise", "")))]
        if len(levels) == 0:
            return None
        rate = facts.get("spairport_network_rate")
        return {
            "percent": percent_of(levels[0]), "dbm": levels[0], "noise": levels[1] if len(levels) > 1 else None,
            "channel": str(facts.get("spairport_network_channel", "")), "standard": str(facts.get("spairport_network_phymode", "")),
            "rate": f"""{rate} Mbps""" if isinstance(rate, int | float) else "",
        }
    return None
