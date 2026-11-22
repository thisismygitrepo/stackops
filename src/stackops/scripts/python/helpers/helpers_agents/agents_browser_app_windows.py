import subprocess
import sys
import time

from stackops.scripts.python.helpers.helpers_agents.agents_browser_app_window_models import BrowserAppWindow, BrowserWindowsUnavailable
from stackops.scripts.python.helpers.helpers_agents.agents_browser_apple_events_windows import focus_apple_events_tab, list_apple_events_windows
from stackops.scripts.python.helpers.helpers_agents.agents_browser_bidi_windows import (
    BidiSessionInUse,
    close_bidi_tabs,
    focus_bidi_tab,
    list_bidi_windows,
    open_bidi_window,
)
from stackops.scripts.python.helpers.helpers_agents.agents_browser_cdp_windows import close_cdp_tabs, focus_cdp_tab, list_cdp_windows, open_cdp_window
from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import (
    BROWSER_ENDPOINT_PROBE_INTERVAL_SECONDS,
    BROWSER_ENDPOINT_STARTUP_TIMEOUT_SECONDS,
    MACOS_ACTIVATE_IGNORING_OTHER_APPS,
    REMOTE_DEBUGGING_LOCALHOST,
    BrowserName,
)
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_runtime import tcp_port_is_open
from stackops.scripts.python.helpers.helpers_agents.browser_launchers.registry import get_browser_launcher


def collect_browser_windows(
    *, browser: BrowserName, process_id: int, port: int | None, without_endpoint: bool
) -> tuple[BrowserAppWindow, ...] | BrowserWindowsUnavailable:
    endpoint_protocol = get_browser_launcher(browser=browser).endpoint_protocol
    if endpoint_protocol == "webdriver":
        return BrowserWindowsUnavailable(reason="unsupported_browser")
    if port is None or not tcp_port_is_open(host=REMOTE_DEBUGGING_LOCALHOST, port=port):
        if without_endpoint and sys.platform == "darwin" and endpoint_protocol == "cdp":
            return list_apple_events_windows(process_id=process_id)
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


def focus_browser_tab(*, browser: BrowserName, process_id: int, port: int | None, window_id: str, tab_id: str) -> None:
    if port is None or not tcp_port_is_open(host=REMOTE_DEBUGGING_LOCALHOST, port=port):
        focus_apple_events_tab(process_id=process_id, window_id=window_id, tab_id=tab_id)
    else:
        match get_browser_launcher(browser=browser).endpoint_protocol:
            case "cdp":
                focus_cdp_tab(port=port, tab_id=tab_id)
            case "webdriver-bidi":
                focus_bidi_tab(port=port, tab_id=tab_id)
            case "webdriver":
                raise ValueError(f"{browser} exposes a WebDriver endpoint, which has no browser tabs to focus")
    if sys.platform == "darwin":
        activated = subprocess.run(
            (
                "/usr/bin/osascript",
                "-l",
                "JavaScript",
                "-e",
                f"""ObjC.import('AppKit');
$.NSRunningApplication.runningApplicationWithProcessIdentifier({process_id}).activateWithOptions({MACOS_ACTIVATE_IGNORING_OTHER_APPS});""",
            ),
            capture_output=True,
            text=True,
            check=False,
        )
        if activated.returncode != 0 or activated.stdout.strip() != "true":
            raise RuntimeError(
                f"""Tab {tab_id} is selected, but macOS did not bring {browser} (PID {process_id}) to the front: {activated.stderr.strip() or activated.stdout.strip()}"""
            )


def _list_windows(*, browser: BrowserName, port: int) -> tuple[BrowserAppWindow, ...]:
    match get_browser_launcher(browser=browser).endpoint_protocol:
        case "cdp":
            return list_cdp_windows(port=port)
        case "webdriver-bidi":
            return list_bidi_windows(port=port)
        case "webdriver":
            raise ValueError(f"{browser} exposes a WebDriver endpoint, which has no browser windows to manage")
