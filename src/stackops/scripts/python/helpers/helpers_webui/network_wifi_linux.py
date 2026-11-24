import shutil

from stackops.scripts.python.helpers.helpers_webui.network_constants import WIFI_COMMAND_SECONDS, WIFI_SCAN_SECONDS
from stackops.scripts.python.helpers.helpers_webui.network_system import read_tool
from stackops.scripts.python.helpers.helpers_webui.network_wifi_model import NOT_CONNECTED, NearbyNetwork, PlatformWifi, WifiCurrent, WifiSignal

# The CLI's Wi-Fi commands talk to NetworkManager on Linux, so the page reads from it too. Every question puts the free text (a network's
# name) last and switches escaping off, so a name with a colon in it still reads whole.
NMCLI = ["nmcli", "--terse", "--escape", "no"]
OPEN_MARKS = frozenset({"", "--"})


def find_adapter() -> str:
    devices = read_tool(command=[*NMCLI, "--fields", "TYPE,STATE,DEVICE", "device", "status"], seconds=WIFI_COMMAND_SECONDS) or ""
    rows = [line.split(":", maxsplit=2) for line in devices.splitlines()]
    wifi = [row for row in rows if len(row) == 3 and row[0] == "wifi"]
    managed = [row for row in wifi if row[1] != "unmanaged"]
    return (managed or wifi)[0][2] if wifi else ""


# The networks NetworkManager knows to be in range. Without `fresh` it answers from what it last saw, at once; with it, it looks again,
# which takes a few seconds. Neither asks the person for anything.
def read_nearby(fresh: bool) -> list[NearbyNetwork] | None:
    listed = read_tool(
        command=[*NMCLI, "--fields", "IN-USE,SIGNAL,SECURITY,SSID", "device", "wifi", "list", "--rescan", "yes" if fresh else "no"],
        seconds=WIFI_SCAN_SECONDS if fresh else WIFI_COMMAND_SECONDS,
    )
    if listed is None:
        return None
    strongest: dict[str, NearbyNetwork] = {}
    for line in listed.splitlines():
        fields = line.split(":", maxsplit=3)
        if len(fields) != 4 or fields[3] == "" or not fields[1].strip().isdecimal():
            continue
        network: NearbyNetwork = {"name": fields[3], "percent": int(fields[1]), "security": "" if fields[2].strip() in OPEN_MARKS else fields[2].strip(), "in_use": fields[0].strip() == "*"}
        known = strongest.get(network["name"])
        # One network is often heard from several access points: the one in use stands for it, or else the strongest.
        if known is None or network["in_use"] or (not known["in_use"] and network["percent"] > known["percent"]):
            strongest[network["name"]] = network
    return sorted(strongest.values(), key=lambda network: (not network["in_use"], -network["percent"]))


def read_state() -> PlatformWifi:
    state: PlatformWifi = {"adapter": "", "radio_on": False, "current": NOT_CONNECTED, "signal": None, "signal_later": False, "remembered": [], "problem": ""}
    if shutil.which("nmcli") is None:
        return {**state, "problem": "NetworkManager's nmcli is not installed. StackOps reads and joins Wi-Fi networks through it on Linux."}
    adapter = find_adapter()
    if adapter == "":
        return {**state, "problem": "NetworkManager sees no Wi-Fi adapter on this machine."}
    radio_on = (read_tool(command=["nmcli", "radio", "wifi"], seconds=WIFI_COMMAND_SECONDS) or "").strip() == "enabled"
    saved = read_tool(command=[*NMCLI, "--fields", "TYPE,NAME", "connection", "show"], seconds=WIFI_COMMAND_SECONDS) or ""
    remembered = [name for kind, _, name in (line.partition(":") for line in saved.splitlines()) if kind == "802-11-wireless" and name != ""]
    in_use = next((network for network in read_nearby(fresh=False) or [] if network["in_use"]), None) if radio_on else None
    current: WifiCurrent = NOT_CONNECTED if in_use is None else {"connected": True, "name": in_use["name"], "name_hidden": False, "security": in_use["security"] or "Open"}
    signal: WifiSignal | None = None if in_use is None else {"percent": in_use["percent"], "dbm": None, "noise": None, "channel": "", "standard": "", "rate": ""}
    return {**state, "adapter": adapter, "radio_on": radio_on, "current": current, "signal": signal, "remembered": remembered}
