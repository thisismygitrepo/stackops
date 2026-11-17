from dataclasses import asdict

from stackops.scripts.python.helpers.helpers_agents.agents_browser_cdp_windows import CdpWindow
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_identity import browser_launch_id, browser_profile_label
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_models import BrowserLaunchResult


def browser_launch_receipt(*, result: BrowserLaunchResult, browser_window: CdpWindow | None) -> dict[str, object]:
    receipt: dict[str, object] = asdict(result)
    receipt["launch_id"] = browser_launch_id(browser=result.browser, profile_path=result.profile_path, port=result.port)
    receipt["profile"] = browser_profile_label(browser=result.browser, profile_path=result.profile_path, port=result.port)
    receipt["endpoint_url"] = f"http://{result.host}:{result.port}"
    receipt["browser_window"] = None if browser_window is None else asdict(browser_window)
    return receipt
