import ctypes
from ctypes import wintypes
from functools import partial
from typing import ClassVar

from stackops.scripts.python.helpers.helpers_window.window_models import WindowAction, WindowEntry


class _WindowPlacement(ctypes.Structure):
    _fields_: ClassVar[list[tuple[str, type[object]]]] = [
        ("length", wintypes.UINT),
        ("flags", wintypes.UINT),
        ("show_command", wintypes.UINT),
        ("minimum_position", wintypes.POINT),
        ("maximum_position", wintypes.POINT),
        ("normal_position", wintypes.RECT),
    ]
    length: int
    flags: int


_USER32 = ctypes.WinDLL("user32", use_last_error=True)
_WINDOW_CALLBACK = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
_USER32.OpenInputDesktop.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
_USER32.OpenInputDesktop.restype = wintypes.HANDLE
_USER32.CloseDesktop.argtypes = [wintypes.HANDLE]
_USER32.CloseDesktop.restype = wintypes.BOOL
_USER32.EnumWindows.argtypes = [_WINDOW_CALLBACK, wintypes.LPARAM]
_USER32.EnumWindows.restype = wintypes.BOOL
_USER32.IsWindowVisible.argtypes = [wintypes.HWND]
_USER32.IsWindowVisible.restype = wintypes.BOOL
_USER32.IsWindow.argtypes = [wintypes.HWND]
_USER32.IsWindow.restype = wintypes.BOOL
_USER32.IsIconic.argtypes = [wintypes.HWND]
_USER32.IsIconic.restype = wintypes.BOOL
_USER32.IsZoomed.argtypes = [wintypes.HWND]
_USER32.IsZoomed.restype = wintypes.BOOL
_USER32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
_USER32.GetWindowTextLengthW.restype = ctypes.c_int
_USER32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
_USER32.GetWindowTextW.restype = ctypes.c_int
_USER32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
_USER32.GetWindowThreadProcessId.restype = wintypes.DWORD
_USER32.GetWindowPlacement.argtypes = [wintypes.HWND, ctypes.POINTER(_WindowPlacement)]
_USER32.GetWindowPlacement.restype = wintypes.BOOL
_USER32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
_USER32.ShowWindow.restype = wintypes.BOOL
_USER32.SetForegroundWindow.argtypes = [wintypes.HWND]
_USER32.SetForegroundWindow.restype = wintypes.BOOL
_USER32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
_USER32.PostMessageW.restype = wintypes.BOOL


def collect_windows() -> list[WindowEntry]:
    desktop = _USER32.OpenInputDesktop(0, False, 0x0001)
    if not desktop:
        raise RuntimeError("Window management requires an interactive Windows desktop session.")
    _USER32.CloseDesktop(desktop)

    entries: list[WindowEntry] = []

    def collect_window(handle: int, _parameter: int) -> bool:
        if not _USER32.IsWindowVisible(handle):
            return True
        title = ctypes.create_unicode_buffer(_USER32.GetWindowTextLengthW(handle) + 1)
        _USER32.GetWindowTextW(handle, title, len(title))
        process_id = wintypes.DWORD()
        _USER32.GetWindowThreadProcessId(handle, ctypes.byref(process_id))
        entries.append(
            WindowEntry(
                app=f"""PID {process_id.value}""",
                title=title.value,
                minimized=bool(_USER32.IsIconic(handle)),
                apply_action=partial(_apply_action, handle),
            )
        )
        return True

    if not _USER32.EnumWindows(_WINDOW_CALLBACK(collect_window), 0):
        raise ctypes.WinError(ctypes.get_last_error())
    return entries


def _unminimize(handle: int) -> None:
    if not _USER32.IsIconic(handle):
        return
    placement = _WindowPlacement()
    placement.length = ctypes.sizeof(placement)
    if not _USER32.GetWindowPlacement(handle, ctypes.byref(placement)):
        raise ctypes.WinError(ctypes.get_last_error())
    _USER32.ShowWindow(handle, 3 if placement.flags & 0x0002 else 9)
    if _USER32.IsIconic(handle):
        raise RuntimeError("Windows could not unminimize the selected window.")


def _apply_action(handle: int, action: WindowAction) -> None:
    if not _USER32.IsWindow(handle):
        raise RuntimeError("The selected window has closed.")
    match action:
        case "minimize":
            _USER32.ShowWindow(handle, 6)
            if not _USER32.IsIconic(handle):
                raise RuntimeError("Windows could not minimize the selected window.")
        case "maximize":
            _USER32.ShowWindow(handle, 3)
            if not _USER32.IsZoomed(handle):
                raise RuntimeError("Windows could not maximize the selected window.")
        case "unminimize":
            _unminimize(handle)
        case "focus":
            _unminimize(handle)
            if not _USER32.SetForegroundWindow(handle):
                raise RuntimeError("Windows did not allow the selected window to take focus.")
        case "close":
            if not _USER32.PostMessageW(handle, 0x0010, 0, 0):
                raise ctypes.WinError(ctypes.get_last_error())
