import getpass
import os
import socket
import sys
from collections.abc import Callable
from typing import Final, Literal, TypedDict

import psutil

# Where each operating system keeps its own programs, in lower case. A process run from one of these counts as part of the system,
# also when it runs under the person's own account, as most of macOS's helpers do. The apps the system ships with are kept elsewhere.
SYSTEM_FOLDERS: Final[dict[str, tuple[str, ...]]] = {
    "darwin": ("/system/library/", "/system/iossupport/", "/usr/libexec/", "/usr/sbin/", "/sbin/", "/library/apple/"),
    "linux": ("/usr/lib/systemd/", "/lib/systemd/"),
    "win32": ("c:\\windows\\",),
}
# Accounts below this number belong to the system, not to a person.
SYSTEM_ACCOUNT_LIMIT: Final[dict[str, int]] = {"darwin": 500, "linux": 1000}
SYSTEM_ACCOUNT_NAMES: Final[frozenset[str]] = frozenset({"system", "local service", "network service"})

type ProcessRole = Literal["", "system", "server", "server_child", "server_parent"]


class ProcessRow(TypedDict):
    pid: int
    started: float
    parent: int
    name: str
    user: str
    status: str
    mine: bool
    role: ProcessRole
    readable: bool
    cpu: float | None
    memory: int | None
    threads: int | None
    command: str
    ports: list[int]


def attempt[Value](read: Callable[[], Value]) -> Value | None:
    try:
        return read()
    except psutil.Error:
        return None


# The ports a process waits on: a TCP socket that accepts connections, or a UDP socket bound to a port and not tied to one remote address.
def waiting_ports(process: psutil.Process) -> list[int]:
    return sorted(
        {
            connection.laddr.port
            for connection in process.net_connections(kind="inet")
            if connection.laddr and connection.laddr.port > 0 and (connection.status == psutil.CONN_LISTEN or (connection.type == socket.SOCK_DGRAM and not connection.raddr))
        }
    )


def account_of(process: psutil.Process, account_names: dict[int, str]) -> tuple[str, bool, bool]:
    if not psutil.POSIX:
        # Windows keeps the owner of its own protected processes to itself. One it will not name counts as the system's.
        name = attempt(process.username) or ""
        bare = name.rpartition("\\")[2].casefold()
        return name, bare == getpass.getuser().casefold(), bare in SYSTEM_ACCOUNT_NAMES or name == ""
    account = process.uids().real
    if account not in account_names:
        # psutil asks the account database on every call, which is the slowest part of a reading; an account's name does not change while the server runs.
        account_names[account] = process.username()
    return account_names[account], account == os.getuid(), account < SYSTEM_ACCOUNT_LIMIT.get(sys.platform, 0)


# One process as the list shows it, or nothing for one that went away while it was being read. What only its owner may read is left empty.
# `cpu` is what psutil measured since it was last asked about this process, which the caller keeps only when that was the reading before.
def read_row(process: psutil.Process, account_names: dict[int, str]) -> ProcessRow | None:
    try:
        with process.oneshot():
            # Asked first on purpose: it is the call that notices a process ID handed to a new process since the last reading.
            parent = process.ppid()
            started = process.create_time()
            name = process.name()
            status = process.status()
            user, mine, system_account = account_of(process=process, account_names=account_names)
            resident = attempt(lambda: process.memory_info().rss)
            cpu = attempt(process.cpu_percent)
            threads = attempt(process.num_threads)
            arguments = attempt(process.cmdline)
            program = attempt(process.exe)
            ports = attempt(lambda: waiting_ports(process)) if resident is not None else None
    except psutil.Error:
        return None
    system_program = program is not None and program.casefold().startswith(SYSTEM_FOLDERS.get(sys.platform, ()))
    return {
        "pid": process.pid,
        "started": started,
        "parent": parent,
        "name": name,
        "user": user,
        "status": status,
        "mine": mine,
        "role": "system" if system_account or system_program or process.pid <= 1 else "",
        "readable": resident is not None,
        "cpu": cpu,
        "memory": resident,
        "threads": threads,
        "command": " ".join(arguments) if arguments else "",
        "ports": ports or [],
    }
