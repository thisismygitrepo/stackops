import json
import subprocess
from typing import TypedDict, cast

from stackops.scripts.python.helpers.helpers_agents.agents_browser_app_window_models import BrowserAppTab, BrowserAppWindow, BrowserWindowsUnavailable
from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import BROWSER_APPLE_EVENTS_TIMEOUT_SECONDS, MACOS_AUTOMATION_DENIED_ERROR


class _ScriptedTab(TypedDict):
    id: str
    title: str | None
    url: str


class _ScriptedWindow(TypedDict):
    id: str
    minimized: bool
    zoomed: bool
    tabs: list[_ScriptedTab]


class _ScriptedListing(TypedDict):
    error: int | None
    windows: list[_ScriptedWindow]


_LIST_WINDOWS_SCRIPT = """ObjC.import('ScriptingBridge');
function run(argv) {
    const app = $.SBApplication.applicationWithProcessIdentifier(Number(argv[0]));
    app.valueForKey('version');
    if (!app.lastError.isNil()) return JSON.stringify({error: Number(app.lastError.code), windows: []});
    const browserWindows = app.valueForKey('windows');
    const windows = [];
    for (let index = 0; index < Number(browserWindows.count); index++) {
        const browserWindow = browserWindows.objectAtIndex(index);
        const tabs = browserWindow.valueForKey('tabs');
        const titles = ObjC.deepUnwrap(tabs.valueForKey('title'));
        const urls = ObjC.deepUnwrap(tabs.valueForKey('URL'));
        windows.push({
            id: String(ObjC.unwrap(browserWindow.valueForKey('id'))),
            minimized: Boolean(ObjC.unwrap(browserWindow.valueForKey('minimized'))),
            zoomed: Boolean(ObjC.unwrap(browserWindow.valueForKey('zoomed'))),
            tabs: ObjC.deepUnwrap(tabs.valueForKey('id')).map((id, position) => ({id: String(id), title: titles[position], url: urls[position]})),
        });
    }
    return JSON.stringify({error: null, windows: windows});
}"""

_FOCUS_TAB_SCRIPT = """ObjC.import('ScriptingBridge');
function run(argv) {
    const browserWindows = $.SBApplication.applicationWithProcessIdentifier(Number(argv[0])).valueForKey('windows');
    for (let index = 0; index < Number(browserWindows.count); index++) {
        const browserWindow = browserWindows.objectAtIndex(index);
        if (String(ObjC.unwrap(browserWindow.valueForKey('id'))) !== argv[1]) continue;
        const position = ObjC.deepUnwrap(browserWindow.valueForKey('tabs').valueForKey('id')).map(String).indexOf(argv[2]);
        if (position < 0) break;
        browserWindow.setValueForKey($.NSNumber.numberWithInteger(position + 1), 'activeTabIndex');
        browserWindow.setValueForKey($.NSNumber.numberWithBool(false), 'minimized');
        browserWindow.setValueForKey($.NSNumber.numberWithInteger(1), 'index');
        return 'focused';
    }
    return 'missing';
}"""


def list_apple_events_windows(*, process_id: int) -> tuple[BrowserAppWindow, ...] | BrowserWindowsUnavailable:
    listing = cast(_ScriptedListing, json.loads(_run_script(script=_LIST_WINDOWS_SCRIPT, arguments=(str(process_id),))))
    if listing["error"] == MACOS_AUTOMATION_DENIED_ERROR:
        return BrowserWindowsUnavailable(reason="automation_denied")
    if listing["error"] is not None:
        raise RuntimeError(f"Browser PID {process_id} rejected Apple events with error {listing['error']}")
    return tuple(
        BrowserAppWindow(
            window_id=window["id"],
            state="minimized" if window["minimized"] else "maximized" if window["zoomed"] else "normal",
            tabs=tuple(BrowserAppTab(tab_id=tab["id"], title=tab["title"], url=tab["url"]) for tab in window["tabs"]),
        )
        for window in listing["windows"]
    )


def focus_apple_events_tab(*, process_id: int, window_id: str, tab_id: str) -> None:
    if _run_script(script=_FOCUS_TAB_SCRIPT, arguments=(str(process_id), window_id, tab_id)) != "focused":
        raise RuntimeError(f"Browser PID {process_id} no longer has tab {tab_id} in window {window_id}")


def _run_script(*, script: str, arguments: tuple[str, ...]) -> str:
    try:
        completed = subprocess.run(
            ("/usr/bin/osascript", "-l", "JavaScript", "-e", script, *arguments),
            capture_output=True,
            text=True,
            check=False,
            timeout=BROWSER_APPLE_EVENTS_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(
            f"Browser PID {arguments[0]} did not answer Apple events within {BROWSER_APPLE_EVENTS_TIMEOUT_SECONDS:g} seconds; "
            "answer the macOS automation prompt if one is open, then retry"
        ) from error
    if completed.returncode != 0:
        raise RuntimeError(f"Apple events to browser PID {arguments[0]} failed: {completed.stderr.strip()}")
    return completed.stdout.strip()
