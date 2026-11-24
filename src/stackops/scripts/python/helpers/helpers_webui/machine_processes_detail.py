import socket
from dataclasses import dataclass
from typing import Final, Literal, TypedDict

import psutil

from stackops.scripts.python.helpers.helpers_webui.machine_processes_rows import attempt

OPEN_FILE_LIMIT: Final[int] = 200
LOCAL_ADDRESSES: Final[frozenset[str]] = frozenset({"::1", "localhost"})
EVERY_ADDRESS: Final[frozenset[str]] = frozenset({"", "*", "0.0.0.0", "::"})

type SocketReach = Literal["local", "network", "address"]


@dataclass(frozen=True, slots=True)
class ProcessProblem:
    status: int
    message: str


class WaitingSocket(TypedDict):
    port: int
    protocol: Literal["TCP", "UDP"]
    address: str
    reach: SocketReach


class ProcessDetail(TypedDict):
    pid: int
    started: float
    readable: bool
    arguments: list[str]
    program: str
    folder: str
    threads: int | None
    waiting: list[WaitingSocket]
    connections: int
    open_files: list[str]
    open_file_count: int


def reach_of(address: str) -> SocketReach:
    if address in LOCAL_ADDRESSES or address.startswith("127."):
        return "local"
    return "network" if address in EVERY_ADDRESS else "address"


def read_sockets(process: psutil.Process) -> tuple[list[WaitingSocket], int]:
    waiting: dict[tuple[int, str, str], WaitingSocket] = {}
    connected = 0
    for connection in process.net_connections(kind="inet"):
        datagram = connection.type == socket.SOCK_DGRAM
        if connection.raddr:
            connected += 1
        elif connection.laddr and connection.laddr.port > 0 and (datagram or connection.status == psutil.CONN_LISTEN):
            protocol: Literal["TCP", "UDP"] = "UDP" if datagram else "TCP"
            waiting[(connection.laddr.port, protocol, connection.laddr.ip)] = {"port": connection.laddr.port, "protocol": protocol, "address": connection.laddr.ip, "reach": reach_of(connection.laddr.ip)}
    return [waiting[key] for key in sorted(waiting)], connected


# What the list leaves out because it costs a call per process: the folder it works in, its open files and its sockets one by one.
# A process is named by its ID together with its start time, so an ID handed to a new process since the page was drawn is never mistaken for the old one.
def read_process_detail(pid: int, started: float) -> ProcessDetail | ProcessProblem:
    try:
        process = psutil.Process(pid)
        if process.create_time() != started:
            return ProcessProblem(status=404, message="This process has ended.")
        with process.oneshot():
            arguments = attempt(process.cmdline)
            program = attempt(process.exe)
            folder = attempt(process.cwd)
            threads = attempt(process.num_threads)
            sockets = attempt(lambda: read_sockets(process))
            files = attempt(lambda: sorted({entry.path for entry in process.open_files()}))
    except psutil.NoSuchProcess:
        return ProcessProblem(status=404, message="This process has ended.")
    waiting, connections = sockets if sockets is not None else ([], 0)
    return {
        "pid": pid,
        "started": started,
        "readable": threads is not None,
        "arguments": arguments or [],
        "program": program or "",
        "folder": folder or "",
        "threads": threads,
        "waiting": waiting,
        "connections": connections,
        "open_files": (files or [])[:OPEN_FILE_LIMIT],
        "open_file_count": len(files or []),
    }
