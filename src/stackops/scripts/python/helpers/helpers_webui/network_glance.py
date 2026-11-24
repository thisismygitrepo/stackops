from typing import TypedDict

from stackops.scripts.python.helpers.helpers_webui.network_forwards import read_forwards
from stackops.scripts.python.helpers.helpers_webui.network_ssh_keys import read_allowed_keys
from stackops.scripts.python.helpers.helpers_webui.network_tunnels import find_binary, read_running
from stackops.scripts.python.helpers.helpers_webui.network_warp import WarpStanding, read_warp_overview
from stackops.scripts.python.helpers.helpers_webui.network_wifi import read_platform
from stackops.scripts.python.helpers.helpers_webui.network_wifi_model import WifiCurrent


# One line for each card on the Network page's overview, so the page says how things stand before a card is opened. Everything here is
# read from this machine and takes a fraction of a second together; nothing asks the network.
class NetworkGlance(TypedDict):
    keys: int
    forwards: int
    wifi: WifiCurrent
    wifi_adapter: bool
    wifi_on: bool
    warp: WarpStanding
    cloudflared: bool
    tunnels_running: int


def read_network_glance() -> NetworkGlance:
    keys, _problem = read_allowed_keys()
    wifi = read_platform()
    return {
        "keys": sum(1 for key in keys if key["problem"] == ""),
        "forwards": len(read_forwards()),
        "wifi": wifi["current"],
        "wifi_adapter": wifi["adapter"] != "",
        "wifi_on": wifi["radio_on"],
        "warp": read_warp_overview()["standing"],
        "cloudflared": find_binary() != "",
        "tunnels_running": len(read_running()),
    }
