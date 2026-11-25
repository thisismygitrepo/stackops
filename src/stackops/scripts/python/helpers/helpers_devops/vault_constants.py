from typing import Literal, TypeAlias, TypedDict

type ClipboardPlatform = Literal["macos", "windows", "wayland", "x11"]
BitwardenCopyField: TypeAlias = Literal["password", "username", "totp"]


class ClipboardCommands(TypedDict):
    copy: tuple[str, ...]
    paste: tuple[str, ...]
    encoding: Literal["utf-8", "utf-16"]


CLIPBOARD_COMMANDS: dict[ClipboardPlatform, ClipboardCommands] = {
    "macos": {"copy": ("pbcopy",), "paste": ("pbpaste",), "encoding": "utf-8"},
    "windows": {"copy": ("clip",), "paste": ("powershell", "-NoLogo", "-NoProfile", "-Command", "Get-Clipboard -Raw"), "encoding": "utf-16"},
    "wayland": {"copy": ("wl-copy",), "paste": ("wl-paste", "--no-newline"), "encoding": "utf-8"},
    "x11": {"copy": ("xclip", "-selection", "clipboard"), "paste": ("xclip", "-selection", "clipboard", "-out"), "encoding": "utf-8"},
}
CLIPBOARD_CLEAR_SECONDS = 45

BITWARDEN_VALUE_FIELD_TYPES: tuple[int, ...] = (0, 1, 2)
BITWARDEN_LINKED_FIELD_TYPE = 3
BITWARDEN_LINKED_LOGIN_FIELDS: dict[int, Literal["username", "password"]] = {100: "username", 101: "password"}
