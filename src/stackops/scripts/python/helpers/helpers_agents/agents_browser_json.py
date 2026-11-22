from dataclasses import asdict

from stackops.scripts.python.helpers.helpers_agents.agents_browser_app_window_models import BrowserAppWindow
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_identity import browser_launch_id, browser_profile_label
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_models import BrowserLaunchResult
from stackops.utils.network.address import InterfaceIPv4Address


def browser_launch_receipt(
    *, result: BrowserLaunchResult, browser_window: BrowserAppWindow | None, lan_address: InterfaceIPv4Address | None
) -> dict[str, object]:
    receipt: dict[str, object] = asdict(result)
    receipt["launch_id"] = browser_launch_id(browser=result.browser, profile_path=result.profile_path, port=result.port)
    receipt["profile"] = browser_profile_label(browser=result.browser, profile_path=result.profile_path, port=result.port)
    endpoint_host = lan_address.ipv4_address if lan_address is not None else result.host
    receipt["endpoint_url"] = f"http://{endpoint_host}:{result.port}"
    receipt["browser_window"] = None if browser_window is None else asdict(browser_window)
    return receipt
