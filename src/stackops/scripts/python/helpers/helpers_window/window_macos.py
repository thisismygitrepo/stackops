import ctypes as ct
import json
import subprocess
import weakref
from functools import partial
from typing import TypedDict, cast

from stackops.scripts.python.helpers.helpers_window import window_macos_api as api
from stackops.scripts.python.helpers.helpers_window.constants import AX_TIMEOUT_SECONDS
from stackops.scripts.python.helpers.helpers_window.window_models import WindowAction, WindowEntry


class DesktopApp(TypedDict):
    pid: int
    name: str


class DesktopScreen(TypedDict):
    x: float
    y: float
    width: float
    height: float


class DesktopInfo(TypedDict):
    apps: list[DesktopApp]
    screens: list[DesktopScreen]


def _desktop_info() -> DesktopInfo:
    script = """ObjC.import('AppKit');
const apps = ObjC.unwrap($.NSWorkspace.sharedWorkspace.runningApplications)
    .filter(app => Number(app.activationPolicy) !== 2)
    .map(app => ({pid: Number(app.processIdentifier), name: ObjC.unwrap(app.localizedName)}));
const displays = ObjC.unwrap($.NSScreen.screens);
const top = displays.length ? displays[0].frame.size.height : 0;
const screens = displays.map(display => {
    const frame = display.visibleFrame;
    return {x: frame.origin.x, y: top - frame.origin.y - frame.size.height,
        width: frame.size.width, height: frame.size.height};
});
JSON.stringify({apps: apps, screens: screens});"""
    result = subprocess.run(
        ["/usr/bin/osascript", "-l", "JavaScript", "-e", script],
        text=True, capture_output=True, check=False, timeout=15,
    )
    if result.returncode != 0:
        raise RuntimeError(f"""macOS could not inspect the desktop: {result.stderr.strip()}""")
    return cast(DesktopInfo, json.loads(result.stdout))


def collect_windows() -> list[WindowEntry]:
    session = api.AX.CGSessionCopyCurrentDictionary()
    if session is None:
        raise RuntimeError("Window management requires a logged-in macOS desktop session.")
    api.CORE.CFRelease(session)
    if not api.AX.AXIsProcessTrusted():
        raise RuntimeError("Allow your terminal or launcher in System Settings > Privacy & Security > Accessibility, then rerun the command.")
    entries: list[WindowEntry] = []
    for app in _desktop_info()["apps"]:
        application = api.AX.AXUIElementCreateApplication(app["pid"])
        try:
            api.check_error(api.AX.AXUIElementSetMessagingTimeout(application, AX_TIMEOUT_SECONDS), "set the window query timeout")
            with api.attribute(application, "AXWindows") as windows:
                if windows is None:
                    continue
                for index in range(api.CORE.CFArrayGetCount(windows)):
                    window = api.CORE.CFArrayGetValueAtIndex(windows, index)
                    entry = WindowEntry(
                        app=app["name"], title=api.read_title(window), minimized=api.read_boolean(window, "AXMinimized"),
                        apply_action=partial(_apply_action, app["pid"], window),
                    )
                    api.CORE.CFRetain(window)
                    weakref.finalize(entry, api.CORE.CFRelease, window)
                    entries.append(entry)
        finally:
            api.CORE.CFRelease(application)
    return entries


def _apply_action(pid: int, window: int, action: WindowAction) -> None:
    match action:
        case "minimize":
            api.set_attribute(window, "AXMinimized", api.CF_TRUE)
        case "unminimize":
            api.set_attribute(window, "AXMinimized", api.CF_FALSE)
        case "maximize":
            _maximize(window)
        case "focus":
            if api.read_boolean(window, "AXMinimized"):
                api.set_attribute(window, "AXMinimized", api.CF_FALSE)
            application = api.AX.AXUIElementCreateApplication(pid)
            try:
                api.set_attribute(application, "AXFrontmost", api.CF_TRUE)
            finally:
                api.CORE.CFRelease(application)
            api.set_attribute(window, "AXMain", api.CF_TRUE)
            api.perform_action(window, "AXRaise")
        case "close":
            with api.attribute(window, "AXCloseButton") as button:
                if button is None:
                    raise RuntimeError("The selected window does not expose a close button.")
                api.perform_action(button, "AXPress")


def _maximize(window: int) -> None:
    if api.read_boolean(window, "AXFullScreen"):
        raise RuntimeError("Exit full screen before maximizing this window to the desktop.")
    screens = _desktop_info()["screens"]
    if not screens:
        raise RuntimeError("No desktop displays are available.")
    x, y, width, height = api.read_geometry(window)
    screen = max(screens, key=lambda item: (
        max(0, min(x + width, item["x"] + item["width"]) - max(x, item["x"]))
        * max(0, min(y + height, item["y"] + item["height"]) - max(y, item["y"]))
    ))
    if api.read_boolean(window, "AXMinimized"):
        api.set_attribute(window, "AXMinimized", api.CF_FALSE)
    for name, value_type, pair in (
        ("AXPosition", 1, (screen["x"], screen["y"])),
        ("AXSize", 2, (screen["width"], screen["height"])),
    ):
        coordinates = (ct.c_double * 2)(*pair)
        value = api.AX.AXValueCreate(value_type, ct.byref(coordinates))
        try:
            api.set_attribute(window, name, value)
        finally:
            api.CORE.CFRelease(value)
