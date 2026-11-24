from stackops.scripts.python.helpers.helpers_webui.network_constants import WIFI_COMMAND_SECONDS
from stackops.scripts.python.helpers.helpers_webui.network_system import read_tool
from stackops.scripts.python.helpers.helpers_webui.network_wifi_model import NOT_CONNECTED, PlatformWifi, WifiCurrent, WifiSignal


# Read from `netsh`, the tool the CLI's Wi-Fi commands use on Windows, and by the same English labels it reads. The list of networks in
# range is left alone: Windows asks for location access before it gives it.
def read_state() -> PlatformWifi:
    state: PlatformWifi = {"adapter": "", "radio_on": False, "current": NOT_CONNECTED, "signal": None, "signal_later": False, "remembered": [], "problem": ""}
    shown = read_tool(command=["netsh", "wlan", "show", "interfaces"], seconds=WIFI_COMMAND_SECONDS)
    if shown is None:
        return {**state, "problem": "Windows reports no Wi-Fi adapter, or its WLAN service is not running."}
    facts: dict[str, str] = {}
    for line in shown.splitlines():
        key, separator, value = line.partition(" : ")
        if separator != "":
            facts.setdefault(key.strip(), value.strip())
    profiles = read_tool(command=["netsh", "wlan", "show", "profiles"], seconds=WIFI_COMMAND_SECONDS) or ""
    remembered = [line.partition(" : ")[2].strip() for line in profiles.splitlines() if "All User Profile" in line and line.partition(" : ")[2].strip() != ""]
    connected = facts.get("State") == "connected" and facts.get("SSID", "") != ""
    current: WifiCurrent = {"connected": True, "name": facts["SSID"], "name_hidden": False, "security": facts.get("Authentication", "")} if connected else NOT_CONNECTED
    strength = facts.get("Signal", "").rstrip("%")
    signal: WifiSignal | None = None
    if connected and strength.isdecimal():
        rate = facts.get("Receive rate (Mbps)", "")
        signal = {"percent": int(strength), "dbm": None, "noise": None, "channel": facts.get("Channel", ""), "standard": facts.get("Radio type", ""), "rate": f"""{rate} Mbps""" if rate != "" else ""}
    return {**state, "adapter": facts.get("Name", ""), "radio_on": "Software Off" not in shown and "Hardware Off" not in shown, "current": current, "signal": signal, "remembered": remembered}
