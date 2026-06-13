from typing import NotRequired, TypedDict


class ProcessInfo(TypedDict):
    pid: int
    name: str
    cmdline: list[str]
    status: str
    cmdline_str: NotRequired[str]
    create_time: NotRequired[float]
    is_direct_command: NotRequired[bool]
    verified_alive: NotRequired[bool]
    memory_mb: NotRequired[float]


class CommandStatus(TypedDict):
    status: str
    running: bool
    processes: list[ProcessInfo]
    command: str
    tab_name: str
    cwd: NotRequired[str]
    error: NotRequired[str]
    pid: NotRequired[int]
    remote: NotRequired[str]
    check_timestamp: NotRequired[str | float]
    method: NotRequired[str]
    raw_output: NotRequired[str]
    verification_method: NotRequired[str]


class StartResult(TypedDict):
    success: bool
    message: NotRequired[str]
    error: NotRequired[str]


class ActiveSessionInfo(TypedDict):
    session_name: str
    is_active: bool
    tab_count: int
    tabs: list[str]
