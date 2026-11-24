from dataclasses import dataclass
from typing import Literal, TypedDict

type UnavailableReason = Literal["permission", "wayland", "unsupported_system"]
type ActionStatus = Literal["done", "gone", "failed"]


# Where a window or a display is, in the desktop's own coordinates: points, counted from the top left corner of the main display.
class FrameView(TypedDict):
    x: float
    y: float
    width: float
    height: float


class ScreenView(TypedDict):
    x: float
    y: float
    width: float
    height: float
    built_in: bool


# One open window as the page lists it. `id` is the CLI's own identifier, valid while the window stays open. `frame` is None where the system
# does not say where a window is. `hidden` marks a window whose whole app is hidden, which macOS does not count as minimized.
class WindowView(TypedDict):
    id: str
    app: str
    title: str
    minimized: bool
    hidden: bool
    full_screen: bool
    frame: FrameView | None


# `screens` is empty where the system does not say where its displays are. `blocked` names the actions that cannot work on this machine, each
# with the reason the page shows on its greyed-out button.
class WindowsView(TypedDict):
    available: Literal[True]
    windows: list[WindowView]
    screens: list[ScreenView]
    blocked: dict[str, str]


# A machine that cannot list its windows at all, as a state of its own and not a failure. `launcher` is the app this server was started from
# when macOS withholds its permission and that app can be told, or empty.
class WindowsUnavailable(TypedDict):
    available: Literal[False]
    reason: UnavailableReason
    launcher: str


# `gone` is a window that closed after the page listed it. `reason` says why a window that is still open could not be changed.
class ActionResult(TypedDict):
    id: str
    status: ActionStatus
    reason: str


class ActionReport(TypedDict):
    results: list[ActionResult]


@dataclass(frozen=True)
class WindowsProblem:
    status: int
    message: str
