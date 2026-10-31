from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SessionEntry:
    name: str
    exited: bool


@dataclass(frozen=True, slots=True)
class TabEntry:
    tab_id: int
    position: int
    name: str
    active: bool


@dataclass(frozen=True, slots=True)
class PaneEntry:
    pane_id: str
    tab_id: int
    tab_position: int
    tab_name: str
    title: str
    command: str
    terminal_command: str
    cwd: str
    exited: bool
    exit_status: int | None
    is_held: bool
    focused: bool
    x: int
    y: int
