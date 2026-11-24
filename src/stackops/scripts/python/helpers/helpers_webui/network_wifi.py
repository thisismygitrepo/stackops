import platform
import subprocess
from typing import TypedDict, cast

from stackops.scripts.python.helpers.helpers_webui.network_constants import WIFI_LOGIN_TAG
from stackops.scripts.python.helpers.helpers_webui.network_wifi_model import NOT_CONNECTED, NearbyNetwork, PlatformWifi, WifiProblem, WifiSignal
from stackops.secrets.paths import SECRETS_DOFILE
from stackops.secrets.search import StackOpsSecretsError, search_logins

CONNECT_BLOCKERS: dict[str, str] = {
    "Darwin": "StackOps cannot join a Wi-Fi network on a Mac yet. Use the Wi-Fi menu in the menu bar.",
}
NEARBY_BLOCKERS: dict[str, str] = {
    "Darwin": "macOS gives the list of networks in range only to apps with location access. Asking for it would put a system prompt on your screen, so this page does not look.",
    "Windows": "Windows asks for location access before it lists the networks in range, so this page does not look.",
}


# A network whose password is kept in the vault, as a login tagged wifi. Only its names are read: `name` is the login's, `ssid` the network's.
class SavedNetwork(TypedDict):
    name: str
    ssid: str


class WifiOverview(PlatformWifi):
    system: str
    saved: list[SavedNetwork]
    saved_problem: str
    connect_blocker: str
    nearby_blocker: str


class ConnectAnswer(TypedDict):
    connected: bool
    name: str


def read_platform() -> PlatformWifi:
    match platform.system():
        case "Darwin":
            from stackops.scripts.python.helpers.helpers_webui.network_wifi_macos import read_state as read_macos

            return read_macos()
        case "Linux":
            from stackops.scripts.python.helpers.helpers_webui.network_wifi_linux import read_state as read_linux

            return read_linux()
        case "Windows":
            from stackops.scripts.python.helpers.helpers_webui.network_wifi_windows import read_state as read_windows

            return read_windows()
        case other:
            return {"adapter": "", "radio_on": False, "current": NOT_CONNECTED, "signal": None, "signal_later": False, "remembered": [], "problem": f"""StackOps cannot read Wi-Fi on {other or "this system"}."""}


def read_saved() -> tuple[list[SavedNetwork], str]:
    if not SECRETS_DOFILE.exists():
        return [], ""
    try:
        logins = search_logins(path=SECRETS_DOFILE, tags=(WIFI_LOGIN_TAG,), keys=("ssid", "password"))
    except (StackOpsSecretsError, OSError):
        return [], "The vault could not be read, so the networks saved in it are not listed. The Vault page says what is wrong with it."
    saved: dict[str, SavedNetwork] = {}
    for login in logins:
        ssid = login["secrets"][0]["keyValues"]["ssid"]
        if isinstance(ssid, str):
            saved.setdefault(login["name"], {"name": login["name"], "ssid": ssid})
    return sorted(saved.values(), key=lambda network: network["name"].lower()), ""


def read_wifi_overview() -> WifiOverview:
    system = platform.system()
    saved, saved_problem = read_saved()
    unsupported = "" if system in ("Linux", "Windows", "Darwin") else f"""StackOps cannot join a Wi-Fi network on {system or "this system"}."""
    return {
        **read_platform(), "system": "macOS" if system == "Darwin" else system, "saved": saved, "saved_problem": saved_problem,
        "connect_blocker": CONNECT_BLOCKERS.get(system, unsupported), "nearby_blocker": NEARBY_BLOCKERS.get(system, unsupported),
    }


def read_wifi_signal() -> WifiSignal | None:
    if platform.system() != "Darwin":
        return read_platform()["signal"]
    from stackops.scripts.python.helpers.helpers_webui.network_wifi_macos import read_signal

    return read_signal()


def read_wifi_nearby(fresh: bool) -> list[NearbyNetwork] | WifiProblem:
    system = platform.system()
    if system != "Linux":
        return WifiProblem(status=409, message=NEARBY_BLOCKERS.get(system, "The networks in range cannot be listed on this system."))
    from stackops.scripts.python.helpers.helpers_webui.network_wifi_linux import read_nearby

    nearby = read_nearby(fresh=fresh)
    return nearby if nearby is not None else WifiProblem(status=502, message="NetworkManager did not list the networks in range.")


# Joins through the functions the CLI's own command calls. `kind` says how: `saved` reads the password from the vault, as `connect-wifi --ssid`
# does; `remembered` asks the system to join a network it already knows; `new` joins with a password typed into the page, which is sent once
# and kept nowhere. The functions print to the server's console and never the password; what comes back to the page is cleared of it all the same.
def connect_wifi(body: object) -> ConnectAnswer | WifiProblem:
    payload = cast(dict[str, object], body) if isinstance(body, dict) else {}
    kind = payload.get("kind")
    name = payload.get("name")
    password = payload.get("password", "")
    if kind not in ("saved", "remembered", "new") or not isinstance(name, str) or name == "" or not isinstance(password, str) or (kind == "new" and password == ""):
        return WifiProblem(status=400, message="Send `kind` as saved, remembered or new, the network's `name`, and for a new one its `password`.")
    blocker = read_wifi_overview()["connect_blocker"]
    if blocker != "":
        return WifiProblem(status=409, message=blocker)
    from stackops.scripts.python.helpers.helpers_network import wifi_conn

    try:
        match kind:
            case "saved":
                if not wifi_conn.try_config_connection(name):
                    return WifiProblem(status=502, message=f"""{name} did not connect. Either it is out of range, or the password kept in the vault is no longer right.""")
            case "remembered":
                wifi_conn.connect(name, name)
            case "new":
                wifi_conn.connect_to_new_network(name, password)
    except subprocess.CalledProcessError as error:
        return WifiProblem(status=502, message=f"""{name} did not connect: the system's Wi-Fi tool stopped with code {error.returncode}.""")
    except (OSError, RuntimeError) as error:
        return WifiProblem(status=502, message=str(error).replace(password, "(the password)") if password != "" else str(error))
    return {"connected": True, "name": name}
