from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SessionEntry:
    name: str
    id: str
    window_count: int
    attached: bool
    saved: bool
    last_active: int


@dataclass(frozen=True, slots=True)
class WindowEntry:
    window_id: str
    index: int
    workspace: int
    display_name: str
    focused: bool
    cwd: str
    agent_state: str
    host: str
    at_prompt: bool | None
    last_exit_code: int | None
    foreground_command: str
    command_seq: int
    running_command: str
    last_command: str
