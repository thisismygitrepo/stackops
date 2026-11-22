from dataclasses import dataclass
from typing import Literal, TypeAlias

BrowserAppWindowState: TypeAlias = Literal["normal", "minimized", "maximized", "fullscreen"]
BrowserWindowsUnavailableReason: TypeAlias = Literal["no_endpoint", "unsupported_browser", "session_in_use", "automation_denied"]


@dataclass(frozen=True)
class BrowserAppTab:
    tab_id: str
    title: str | None
    url: str


@dataclass(frozen=True)
class BrowserAppWindow:
    window_id: str
    state: BrowserAppWindowState
    tabs: tuple[BrowserAppTab, ...]


@dataclass(frozen=True)
class BrowserWindowsUnavailable:
    reason: BrowserWindowsUnavailableReason
