import time

from stackops.scripts.python.helpers.helpers_agents.agents_browser_app_window_models import BrowserAppWindow, BrowserWindowsUnavailable
from stackops.scripts.python.helpers.helpers_agents.agents_browser_bidi_windows import BidiSessionInUse, close_bidi_tabs, list_bidi_windows, open_bidi_window
from stackops.scripts.python.helpers.helpers_agents.agents_browser_cdp_windows import close_cdp_tabs, list_cdp_windows, open_cdp_window
from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import (
    BROWSER_ENDPOINT_PROBE_INTERVAL_SECONDS,
    BROWSER_ENDPOINT_STARTUP_TIMEOUT_SECONDS,
    REMOTE_DEBUGGING_LOCALHOST,
    BrowserName,
)
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_runtime import tcp_port_is_open
from stackops.scripts.python.helpers.helpers_agents.browser_launchers.registry import get_browser_launcher


def collect_browser_windows(*, browser: BrowserName, port: int | None) -> tuple[BrowserAppWindow, ...] | BrowserWindowsUnavailable:
    if get_browser_launcher(browser=browser).endpoint_protocol == "webdriver":
        return BrowserWindowsUnavailable(reason="unsupported_browser")
    if port is None or not tcp_port_is_open(host=REMOTE_DEBUGGING_LOCALHOST, port=port):
        return BrowserWindowsUnavailable(reason="no_endpoint")
    try:
        return _list_windows(browser=browser, port=port)
    except BidiSessionInUse:
        return BrowserWindowsUnavailable(reason="session_in_use")


def claim_browser_window(*, browser: BrowserName, port: int, open_new: bool) -> BrowserAppWindow:
    if open_new:
        match get_browser_launcher(browser=browser).endpoint_protocol:
            case "cdp":
                return open_cdp_window(port=port)
            case "webdriver-bidi":
                return open_bidi_window(port=port)
            case "webdriver":
                raise ValueError(f"{browser} exposes a WebDriver endpoint, which has no browser windows to manage")
    deadline = time.monotonic() + BROWSER_ENDPOINT_STARTUP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        windows = _list_windows(browser=browser, port=port)
        if windows:
            return windows[0]
        time.sleep(BROWSER_ENDPOINT_PROBE_INTERVAL_SECONDS)
    raise RuntimeError(f"{browser} on port {port} did not open a window within {BROWSER_ENDPOINT_STARTUP_TIMEOUT_SECONDS:g} seconds")


def close_browser_window(*, browser: BrowserName, port: int, window_id: str) -> BrowserAppWindow:
    windows = _list_windows(browser=browser, port=port)
    window = next((candidate for candidate in windows if candidate.window_id == window_id), None)
    if window is None:
        open_window_ids = ", ".join(candidate.window_id for candidate in windows)
        raise RuntimeError(f"No {browser} window {window_id} on port {port}; open windows: {open_window_ids or 'none'}")
    if len(windows) == 1:
        raise RuntimeError(
            f"Window {window_id} is the last {browser} window on port {port}; closing it can quit the browser. Close the launch by --port or --profile instead."
        )
    match get_browser_launcher(browser=browser).endpoint_protocol:
        case "cdp":
            close_cdp_tabs(port=port, tabs=window.tabs)
        case "webdriver-bidi":
            close_bidi_tabs(port=port, tabs=window.tabs)
        case "webdriver":
            raise ValueError(f"{browser} exposes a WebDriver endpoint, which has no browser windows to manage")
    return window


def _list_windows(*, browser: BrowserName, port: int) -> tuple[BrowserAppWindow, ...]:
    match get_browser_launcher(browser=browser).endpoint_protocol:
        case "cdp":
            return list_cdp_windows(port=port)
        case "webdriver-bidi":
            return list_bidi_windows(port=port)
        case "webdriver":
            raise ValueError(f"{browser} exposes a WebDriver endpoint, which has no browser windows to manage")
