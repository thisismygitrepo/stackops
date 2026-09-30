import ctypes as ct
from collections.abc import Generator
from contextlib import contextmanager


CORE = ct.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
AX = ct.CDLL("/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices")

CORE.CFRelease.argtypes = [ct.c_void_p]
CORE.CFRelease.restype = None
CORE.CFRetain.argtypes = [ct.c_void_p]
CORE.CFRetain.restype = ct.c_void_p
CORE.CFStringCreateWithCString.argtypes = [ct.c_void_p, ct.c_char_p, ct.c_uint32]
CORE.CFStringCreateWithCString.restype = ct.c_void_p
CORE.CFStringGetLength.argtypes = [ct.c_void_p]
CORE.CFStringGetLength.restype = ct.c_long
CORE.CFStringGetCString.argtypes = [ct.c_void_p, ct.c_char_p, ct.c_long, ct.c_uint32]
CORE.CFStringGetCString.restype = ct.c_bool
CORE.CFArrayGetCount.argtypes = [ct.c_void_p]
CORE.CFArrayGetCount.restype = ct.c_long
CORE.CFArrayGetValueAtIndex.argtypes = [ct.c_void_p, ct.c_long]
CORE.CFArrayGetValueAtIndex.restype = ct.c_void_p
CORE.CFBooleanGetValue.argtypes = [ct.c_void_p]
CORE.CFBooleanGetValue.restype = ct.c_bool
AX.AXIsProcessTrusted.argtypes = []
AX.AXIsProcessTrusted.restype = ct.c_bool
AX.CGSessionCopyCurrentDictionary.argtypes = []
AX.CGSessionCopyCurrentDictionary.restype = ct.c_void_p
AX.AXUIElementCreateApplication.argtypes = [ct.c_int]
AX.AXUIElementCreateApplication.restype = ct.c_void_p
AX.AXUIElementSetMessagingTimeout.argtypes = [ct.c_void_p, ct.c_float]
AX.AXUIElementSetMessagingTimeout.restype = ct.c_int
AX.AXUIElementCopyAttributeValue.argtypes = [ct.c_void_p, ct.c_void_p, ct.POINTER(ct.c_void_p)]
AX.AXUIElementCopyAttributeValue.restype = ct.c_int
AX.AXUIElementSetAttributeValue.argtypes = [ct.c_void_p, ct.c_void_p, ct.c_void_p]
AX.AXUIElementSetAttributeValue.restype = ct.c_int
AX.AXUIElementPerformAction.argtypes = [ct.c_void_p, ct.c_void_p]
AX.AXUIElementPerformAction.restype = ct.c_int
AX.AXValueCreate.argtypes = [ct.c_int, ct.c_void_p]
AX.AXValueCreate.restype = ct.c_void_p
AX.AXValueGetValue.argtypes = [ct.c_void_p, ct.c_int, ct.c_void_p]
AX.AXValueGetValue.restype = ct.c_bool

CF_UTF8 = 0x08000100
CF_TRUE = ct.c_void_p.in_dll(CORE, "kCFBooleanTrue").value
CF_FALSE = ct.c_void_p.in_dll(CORE, "kCFBooleanFalse").value


class AccessibilityError(RuntimeError):
    def __init__(self, code: int, operation: str) -> None:
        self.code = code
        super().__init__(f"""macOS could not {operation} (Accessibility error {code}).""")


def check_error(error: int, operation: str) -> None:
    if error != 0:
        raise AccessibilityError(code=error, operation=operation)


@contextmanager
def attribute(element: int, name: str) -> Generator[int | None, None, None]:
    key = CORE.CFStringCreateWithCString(None, name.encode(), CF_UTF8)
    value = ct.c_void_p()
    try:
        error = AX.AXUIElementCopyAttributeValue(element, key, ct.byref(value))
        if error not in {-25205, -25212}:
            check_error(error, f"""read {name}""")
        yield value.value
    finally:
        CORE.CFRelease(key)
        if value.value is not None:
            CORE.CFRelease(value.value)


def set_attribute(element: int, name: str, value: int | None) -> None:
    key = CORE.CFStringCreateWithCString(None, name.encode(), CF_UTF8)
    try:
        check_error(AX.AXUIElementSetAttributeValue(element, key, value), f"""set {name}; this window may not support the action""")
    finally:
        CORE.CFRelease(key)


def perform_action(element: int, name: str) -> None:
    key = CORE.CFStringCreateWithCString(None, name.encode(), CF_UTF8)
    try:
        check_error(AX.AXUIElementPerformAction(element, key), f"""perform {name}""")
    finally:
        CORE.CFRelease(key)


def read_title(window: int) -> str:
    with attribute(window, "AXTitle") as value:
        if value is None:
            return ""
        buffer = ct.create_string_buffer(CORE.CFStringGetLength(value) * 4 + 1)
        if not CORE.CFStringGetCString(value, buffer, len(buffer), CF_UTF8):
            raise RuntimeError("macOS could not read the selected window's title.")
        return buffer.value.decode("utf-8")


def read_boolean(window: int, name: str) -> bool:
    with attribute(window, name) as value:
        return value is not None and bool(CORE.CFBooleanGetValue(value))


def read_geometry(window: int) -> tuple[float, float, float, float]:
    coordinates: list[float] = []
    for name, value_type in (("AXPosition", 1), ("AXSize", 2)):
        with attribute(window, name) as value:
            pair = (ct.c_double * 2)()
            if value is None or not AX.AXValueGetValue(value, value_type, ct.byref(pair)):
                raise RuntimeError("The window does not expose its position and size.")
            coordinates.extend(pair)
    return coordinates[0], coordinates[1], coordinates[2], coordinates[3]
