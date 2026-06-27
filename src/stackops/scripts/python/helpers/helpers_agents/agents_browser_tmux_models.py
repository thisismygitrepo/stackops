from dataclasses import dataclass
from typing import Final


STACKOPS_BROWSER_TMUX_SESSION_NAME: Final[str] = "stackops-browser"
TMUX_FIELD_SEPARATOR: Final[str] = "\x1f"


@dataclass(frozen=True)
class BrowserTmuxLaunch:
    session_name: str
    browser_window_name: str
    relay_window_name: str | None
    attach_command: tuple[str, ...]


@dataclass(frozen=True)
class BrowserTmuxMetadata:
    launch_id: str
    role: str
    browser: str
    profile: str
    profile_path: str
    host: str
    port: str
    browser_port: str
    lan: str
    prompt_path: str


@dataclass(frozen=True)
class BrowserTmuxPaneStatus:
    session_name: str
    window_index: str
    window_id: str
    window_name: str
    pane_index: str
    pane_id: str
    pane_pid: str
    pane_current_command: str
    pane_dead: bool
    pane_current_path: str
    metadata: BrowserTmuxMetadata


@dataclass(frozen=True)
class RawTmuxPane:
    session_name: str
    window_index: str
    window_id: str
    window_name: str
    pane_index: str
    pane_id: str
    pane_pid: str
    pane_current_command: str
    pane_dead: bool
    pane_current_path: str
