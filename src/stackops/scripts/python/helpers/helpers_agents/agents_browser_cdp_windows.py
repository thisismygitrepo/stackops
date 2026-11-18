from collections.abc import Generator
from contextlib import contextmanager
import json
from typing import TypedDict, cast
from urllib.request import urlopen

from websockets.exceptions import WebSocketException
from websockets.sync.client import connect
from websockets.sync.connection import Connection

from stackops.scripts.python.helpers.helpers_agents.agents_browser_app_window_models import BrowserAppTab, BrowserAppWindow, BrowserAppWindowState
from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import BROWSER_CDP_REQUEST_TIMEOUT_SECONDS, REMOTE_DEBUGGING_LOCALHOST
from stackops.scripts.python.helpers.helpers_agents.agents_browser_endpoint_rpc import call_browser_endpoint


class _TargetInfo(TypedDict):
    targetId: str
    type: str
    title: str
    url: str


class _WindowBounds(TypedDict):
    windowState: BrowserAppWindowState


class _TargetWindow(TypedDict):
    windowId: int
    bounds: _WindowBounds


def list_cdp_windows(*, port: int) -> tuple[BrowserAppWindow, ...]:
    with _cdp_session(port=port) as connection:
        listed = cast(dict[str, list[_TargetInfo]], _call(connection=connection, method="Target.getTargets", params={})["result"])
        tabs_by_window: dict[int, list[BrowserAppTab]] = {}
        state_by_window: dict[int, BrowserAppWindowState] = {}
        for target in listed["targetInfos"]:
            if target["type"] != "page":
                continue
            placed = _call(connection=connection, method="Browser.getWindowForTarget", params={"targetId": target["targetId"]})
            if "result" not in placed:
                continue
            target_window = cast(_TargetWindow, placed["result"])
            tabs_by_window.setdefault(target_window["windowId"], []).append(
                BrowserAppTab(tab_id=target["targetId"], title=target["title"], url=target["url"])
            )
            state_by_window[target_window["windowId"]] = target_window["bounds"]["windowState"]
        return tuple(
            BrowserAppWindow(window_id=str(window_id), state=state_by_window[window_id], tabs=tuple(tabs))
            for window_id, tabs in sorted(tabs_by_window.items())
        )


def open_cdp_window(*, port: int) -> BrowserAppWindow:
    with _cdp_session(port=port) as connection:
        created = _call(connection=connection, method="Target.createTarget", params={"url": "about:blank", "newWindow": True})
        if "result" not in created:
            raise RuntimeError(f"Browser on CDP port {port} refused to open a new window: {created.get('error')}")
        tab_id = cast(dict[str, str], created["result"])["targetId"]
        placed = _call(connection=connection, method="Browser.getWindowForTarget", params={"targetId": tab_id})
        if "result" not in placed:
            raise RuntimeError(f"Browser on CDP port {port} opened tab {tab_id} without a window: {placed.get('error')}")
        target_window = cast(_TargetWindow, placed["result"])
        return BrowserAppWindow(
            window_id=str(target_window["windowId"]),
            state=target_window["bounds"]["windowState"],
            tabs=(BrowserAppTab(tab_id=tab_id, title="about:blank", url="about:blank"),),
        )


def close_cdp_tabs(*, port: int, tabs: tuple[BrowserAppTab, ...]) -> None:
    with _cdp_session(port=port) as connection:
        for tab in tabs:
            closed = _call(connection=connection, method="Target.closeTarget", params={"targetId": tab.tab_id})
            if "result" not in closed:
                raise RuntimeError(f"Browser on CDP port {port} could not close tab {tab.tab_id}: {closed.get('error')}")


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
    return call_browser_endpoint(connection=connection, method=method, params=params, timeout_seconds=BROWSER_CDP_REQUEST_TIMEOUT_SECONDS)
