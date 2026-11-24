import ctypes as ct
from functools import partial
from pathlib import Path
from typing import cast

import psutil

from stackops.scripts.python.helpers.helpers_webui.machine_windows_constants import MAX_DISPLAYS
from stackops.scripts.python.helpers.helpers_webui.machine_windows_models import FrameView, ScreenView, WindowView
from stackops.scripts.python.helpers.helpers_window import window_macos_api as api
from stackops.scripts.python.helpers.helpers_window.constants import AX_TIMEOUT_SECONDS
from stackops.scripts.python.helpers.helpers_window.window_models import WindowEntry


class _DisplayBounds(ct.Structure):
    _fields_ = [("x", ct.c_double), ("y", ct.c_double), ("width", ct.c_double), ("height", ct.c_double)]
    x: float
    y: float
    width: float
    height: float


GRAPHICS = ct.CDLL("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
GRAPHICS.CGGetActiveDisplayList.argtypes = [ct.c_uint32, ct.POINTER(ct.c_uint32), ct.POINTER(ct.c_uint32)]
GRAPHICS.CGGetActiveDisplayList.restype = ct.c_int32
GRAPHICS.CGDisplayBounds.argtypes = [ct.c_uint32]
GRAPHICS.CGDisplayBounds.restype = _DisplayBounds
GRAPHICS.CGDisplayIsBuiltin.argtypes = [ct.c_uint32]
GRAPHICS.CGDisplayIsBuiltin.restype = ct.c_uint32


# Every display in use, whole, in the coordinates macOS reports window positions in. The CLI reads the usable part of each display through a
# script it starts for the purpose; this asks the system directly, which costs nothing and gives the full display the map draws.
def read_macos_screens() -> list[ScreenView]:
    displays = (ct.c_uint32 * MAX_DISPLAYS)()
    count = ct.c_uint32()
    if GRAPHICS.CGGetActiveDisplayList(MAX_DISPLAYS, displays, ct.byref(count)) != 0:
        raise RuntimeError("macOS could not list the displays.")
    screens: list[ScreenView] = []
    for display in displays[: count.value]:
        bounds: _DisplayBounds = GRAPHICS.CGDisplayBounds(display)
        screens.append({"x": bounds.x, "y": bounds.y, "width": bounds.width, "height": bounds.height, "built_in": bool(GRAPHICS.CGDisplayIsBuiltin(display))})
    return screens


# An app that does not answer in time counts as showing.
def _app_hidden(process: int) -> bool:
    application = api.AX.AXUIElementCreateApplication(process)
    try:
        api.check_error(api.AX.AXUIElementSetMessagingTimeout(application, AX_TIMEOUT_SECONDS), "set the window query timeout")
        return api.read_boolean(application, "AXHidden")
    except api.AccessibilityError:
        return False
    finally:
        api.CORE.CFRelease(application)


# The CLI's entry keeps its handle on the window only inside `apply_action`, a `partial` over the app's process and that handle. Reading it from
# there is what lets the page say where a window is without asking every app for its windows a second time.
def describe_macos_windows(entries: list[WindowEntry]) -> list[WindowView]:
    hidden_apps: dict[int, bool] = {}
    windows: list[WindowView] = []
    for entry in entries:
        match cast(object, entry.apply_action):
            case partial(args=(int() as process, int() as element)):
                pass
            case _:
                raise RuntimeError("The window helper no longer keeps a window's handle where this page reads it.")
        if process not in hidden_apps:
            hidden_apps[process] = _app_hidden(process)
        frame: FrameView | None = None
        full_screen = False
        try:
            x, y, width, height = api.read_geometry(element)
            frame = {"x": x, "y": y, "width": width, "height": height}
            full_screen = api.read_boolean(element, "AXFullScreen")
        except RuntimeError:
            # A window that closed or stopped answering since the list was made keeps its row, without a place.
            pass
        windows.append(
            {
                "id": entry.id, "app": entry.app, "title": entry.title, "minimized": entry.minimized,
                "hidden": hidden_apps[process], "full_screen": full_screen, "frame": frame,
            }
        )
    return windows


# macOS gives the Accessibility permission to the app a program was started from, not to the program. That is usually the outermost app among
# this server's parents: the terminal, or the editor whose terminal it runs in. An app inside a framework is a helper, as Python's own launcher
# is, and never the one to allow. Empty when no parent is an app, as under a terminal multiplexer that outlived its terminal.
def launcher_app() -> str:
    for ancestor in reversed(psutil.Process().parents()):
        try:
            executable = ancestor.exe()
        except psutil.Error:
            continue
        bundle = next((part for part in Path(executable).parts if part.endswith(".app")), None)
        if bundle is not None and ".framework" not in executable:
            return bundle.removesuffix(".app")
    return ""
