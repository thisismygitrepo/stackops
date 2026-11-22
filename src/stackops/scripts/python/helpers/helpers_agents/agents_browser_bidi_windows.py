from collections.abc import Generator
from contextlib import contextmanager
import json
from typing import TypedDict, cast

from websockets.exceptions import WebSocketException
from websockets.sync.client import connect
from websockets.sync.connection import Connection

from stackops.scripts.python.helpers.helpers_agents.agents_browser_app_window_models import BrowserAppTab, BrowserAppWindow, BrowserAppWindowState
from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import BROWSER_BIDI_REQUEST_TIMEOUT_SECONDS, REMOTE_DEBUGGING_LOCALHOST
from stackops.scripts.python.helpers.helpers_agents.agents_browser_endpoint_rpc import call_browser_endpoint


class BidiSessionInUse(RuntimeError):
    pass


class _ClientWindowInfo(TypedDict):
    clientWindow: str
    state: BrowserAppWindowState


class _ContextInfo(TypedDict):
    context: str
    clientWindow: str
    url: str


def list_bidi_windows(*, port: int) -> tuple[BrowserAppWindow, ...]:
    with _bidi_session(port=port) as connection:
        return _read_windows(connection=connection)


def open_bidi_window(*, port: int) -> BrowserAppWindow:
    with _bidi_session(port=port) as connection:
        tab_id = cast(str, _command(connection=connection, method="browsingContext.create", params={"type": "window"})["context"])
        window = next(
            (candidate for candidate in _read_windows(connection=connection) if any(tab.tab_id == tab_id for tab in candidate.tabs)), None
        )
        if window is None:
            raise RuntimeError(f"Firefox on port {port} opened tab {tab_id}, but no window lists it")
        return window


def close_bidi_tabs(*, port: int, tabs: tuple[BrowserAppTab, ...]) -> None:
    with _bidi_session(port=port) as connection:
        for tab in tabs:
            _command(connection=connection, method="browsingContext.close", params={"context": tab.tab_id})


def focus_bidi_tab(*, port: int, tab_id: str) -> None:
    with _bidi_session(port=port) as connection:
        _command(connection=connection, method="browsingContext.activate", params={"context": tab_id})


@contextmanager
def _bidi_session(*, port: int) -> Generator[Connection, None, None]:
    try:
        with connect(
            f"ws://{REMOTE_DEBUGGING_LOCALHOST}:{port}/session", open_timeout=BROWSER_BIDI_REQUEST_TIMEOUT_SECONDS, compression=None, max_size=None
        ) as connection:
            started = call_browser_endpoint(
                connection=connection, method="session.new", params={"capabilities": {}}, timeout_seconds=BROWSER_BIDI_REQUEST_TIMEOUT_SECONDS
            )
            if started.get("error") == "session not created":
                raise BidiSessionInUse(
                    f"Firefox on port {port} already has an automation session attached; its windows can be read or changed only after that session ends"
                )
            if started.get("type") != "success":
                raise RuntimeError(f"Firefox on port {port} refused a WebDriver BiDi session: {started.get('error')}: {started.get('message')}")
            try:
                yield connection
            finally:
                _command(connection=connection, method="session.end", params={})
    except (OSError, json.JSONDecodeError, KeyError, WebSocketException) as error:
        raise RuntimeError(
            f"WebDriver BiDi endpoint on port {port} could not be queried for browser windows (Firefox 138 or newer is required): {error}"
        ) from error


def _command(*, connection: Connection, method: str, params: dict[str, object]) -> dict[str, object]:
    reply = call_browser_endpoint(connection=connection, method=method, params=params, timeout_seconds=BROWSER_BIDI_REQUEST_TIMEOUT_SECONDS)
    if reply.get("type") != "success":
        raise RuntimeError(f"Firefox rejected {method}: {reply.get('error')}: {reply.get('message')}")
    return cast(dict[str, object], reply["result"])


def _read_windows(*, connection: Connection) -> tuple[BrowserAppWindow, ...]:
    client_windows = cast(list[_ClientWindowInfo], _command(connection=connection, method="browser.getClientWindows", params={})["clientWindows"])
    contexts = cast(list[_ContextInfo], _command(connection=connection, method="browsingContext.getTree", params={"maxDepth": 0})["contexts"])
    return tuple(
        BrowserAppWindow(
            window_id=client_window["clientWindow"],
            state=client_window["state"],
            tabs=tuple(
                BrowserAppTab(tab_id=context["context"], title=None, url=context["url"])
                for context in contexts
                if context["clientWindow"] == client_window["clientWindow"]
            ),
        )
        for client_window in client_windows
    )
