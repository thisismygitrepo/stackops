from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from itertools import count
import json
import time
from typing import Final, Literal, TypeAlias, TypedDict, cast
from urllib.request import urlopen

from websockets.exceptions import WebSocketException
from websockets.sync.client import connect
from websockets.sync.connection import Connection

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import (
    BROWSER_CDP_REQUEST_TIMEOUT_SECONDS,
    BROWSER_ENDPOINT_PROBE_INTERVAL_SECONDS,
    BROWSER_ENDPOINT_STARTUP_TIMEOUT_SECONDS,
    REMOTE_DEBUGGING_LOCALHOST,
    BrowserName,
)
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_runtime import tcp_port_is_open
from stackops.scripts.python.helpers.helpers_agents.browser_launchers.registry import get_browser_launcher

CdpWindowState: TypeAlias = Literal["normal", "minimized", "maximized", "fullscreen"]


@dataclass(frozen=True)
class CdpTab:
    target_id: str
    title: str
    url: str


@dataclass(frozen=True)
class CdpWindow:
    window_id: int
    state: CdpWindowState
    tabs: tuple[CdpTab, ...]


class _TargetInfo(TypedDict):
    targetId: str
    type: str
    title: str
    url: str


class _WindowBounds(TypedDict):
    windowState: CdpWindowState


class _TargetWindow(TypedDict):
    windowId: int
    bounds: _WindowBounds


_REQUEST_IDS: Final[count[int]] = count(1)


def collect_browser_windows(*, browser: BrowserName, port: int | None) -> tuple[CdpWindow, ...] | None:
    if port is None or get_browser_launcher(browser=browser).endpoint_protocol != "cdp":
        return None
    if not tcp_port_is_open(host=REMOTE_DEBUGGING_LOCALHOST, port=port):
        return None
    return list_cdp_windows(port=port)


def list_cdp_windows(*, port: int) -> tuple[CdpWindow, ...]:
    with _cdp_session(port=port) as connection:
        return _read_windows(connection=connection)


def claim_cdp_window(*, port: int, open_new: bool) -> CdpWindow:
    if open_new:
        with _cdp_session(port=port) as connection:
            created = _call(connection=connection, method="Target.createTarget", params={"url": "about:blank", "newWindow": True})
            if "result" not in created:
                raise RuntimeError(f"Browser on CDP port {port} refused to open a new window: {created.get('error')}")
            target_id = cast(dict[str, str], created["result"])["targetId"]
            placed = _call(connection=connection, method="Browser.getWindowForTarget", params={"targetId": target_id})
            if "result" not in placed:
                raise RuntimeError(f"Browser on CDP port {port} opened tab {target_id} without a window: {placed.get('error')}")
            target_window = cast(_TargetWindow, placed["result"])
            return CdpWindow(
                window_id=target_window["windowId"],
                state=target_window["bounds"]["windowState"],
                tabs=(CdpTab(target_id=target_id, title="about:blank", url="about:blank"),),
            )
    deadline = time.monotonic() + BROWSER_ENDPOINT_STARTUP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        windows = list_cdp_windows(port=port)
        if windows:
            return windows[0]
        time.sleep(BROWSER_ENDPOINT_PROBE_INTERVAL_SECONDS)
    raise RuntimeError(f"Browser on CDP port {port} did not open a window within {BROWSER_ENDPOINT_STARTUP_TIMEOUT_SECONDS:g} seconds")


def close_cdp_window(*, port: int, window_id: int) -> CdpWindow:
    with _cdp_session(port=port) as connection:
        windows = _read_windows(connection=connection)
        window = next((candidate for candidate in windows if candidate.window_id == window_id), None)
        if window is None:
            open_window_ids = ", ".join(str(candidate.window_id) for candidate in windows)
            raise RuntimeError(f"No browser window {window_id} on CDP port {port}; open windows: {open_window_ids or 'none'}")
        if len(windows) == 1:
            raise RuntimeError(
                f"Window {window_id} is the last window on CDP port {port}; closing it can quit the browser. Close the launch by --port or --profile instead."
            )
        for tab in window.tabs:
            closed = _call(connection=connection, method="Target.closeTarget", params={"targetId": tab.target_id})
            if "result" not in closed:
                raise RuntimeError(f"Browser on CDP port {port} could not close tab {tab.target_id} of window {window_id}: {closed.get('error')}")
        return window


@contextmanager
def _cdp_session(*, port: int) -> Generator[Connection, None, None]:
    try:
        with urlopen(f"http://{REMOTE_DEBUGGING_LOCALHOST}:{port}/json/version", timeout=BROWSER_CDP_REQUEST_TIMEOUT_SECONDS) as response:
            web_socket_url = cast(dict[str, str], json.loads(response.read()))["webSocketDebuggerUrl"]
        with connect(web_socket_url, open_timeout=BROWSER_CDP_REQUEST_TIMEOUT_SECONDS, max_size=None) as connection:
            yield connection
    except (OSError, json.JSONDecodeError, KeyError, WebSocketException) as error:
        raise RuntimeError(f"Chrome DevTools Protocol endpoint on port {port} could not be queried for browser windows: {error}") from error


def _call(*, connection: Connection, method: str, params: dict[str, object]) -> dict[str, object]:
    request_id = next(_REQUEST_IDS)
    connection.send(json.dumps({"id": request_id, "method": method, "params": params}))
    while True:
        reply = cast(dict[str, object], json.loads(connection.recv(timeout=BROWSER_CDP_REQUEST_TIMEOUT_SECONDS)))
        if reply.get("id") == request_id:
            return reply


def _read_windows(*, connection: Connection) -> tuple[CdpWindow, ...]:
    listed = cast(dict[str, list[_TargetInfo]], _call(connection=connection, method="Target.getTargets", params={})["result"])
    tabs_by_window: dict[int, list[CdpTab]] = {}
    state_by_window: dict[int, CdpWindowState] = {}
    for target in listed["targetInfos"]:
        if target["type"] != "page":
            continue
        placed = _call(connection=connection, method="Browser.getWindowForTarget", params={"targetId": target["targetId"]})
        if "result" not in placed:
            continue
        target_window = cast(_TargetWindow, placed["result"])
        tabs_by_window.setdefault(target_window["windowId"], []).append(CdpTab(target_id=target["targetId"], title=target["title"], url=target["url"]))
        state_by_window[target_window["windowId"]] = target_window["bounds"]["windowState"]
    return tuple(
        CdpWindow(window_id=window_id, state=state_by_window[window_id], tabs=tuple(tabs)) for window_id, tabs in sorted(tabs_by_window.items())
    )
