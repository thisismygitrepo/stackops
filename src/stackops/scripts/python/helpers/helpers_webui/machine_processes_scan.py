import getpass
import os
import socket
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Final, Literal, TypedDict

import psutil

# Two pages asking at nearly the same moment share one reading, so each processor figure still covers a real stretch of time.
SNAPSHOT_REUSE_SECONDS: Final[float] = 1.0
# Processor use is what a process did since the reading before. Past this gap that says nothing about now, so the figures are left out once.
CPU_WINDOW_SECONDS: Final[float] = 20.0
SYSTEM_FOLDERS: Final[dict[str, tuple[str, ...]]] = {
    "darwin": ("/system/library/", "/system/iossupport/", "/usr/libexec/", "/usr/sbin/", "/sbin/", "/library/apple/"),
    "linux": ("/usr/lib/systemd/", "/lib/systemd/"),
    "win32": ("c:\\windows\\",),
}
# Accounts below this number belong to the system, not to a person.
SYSTEM_ACCOUNT_LIMIT: Final[dict[str, int]] = {"darwin": 500, "linux": 1000}
SYSTEM_ACCOUNT_NAMES: Final[frozenset[str]] = frozenset({"system", "local service", "network service"})

type ProcessRole = Literal["", "system", "server", "server_child", "server_parent"]
type ProcessKey = tuple[int, float]


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


class MachineLoad(TypedDict):
    cores: int
    cpu: float | None
    memory_total: int
    memory_used: int


class ProcessSnapshot(TypedDict):
    taken_at: float
    user: str
    privileged: bool
    machine: MachineLoad
    processes: list[ProcessRow]


@dataclass(slots=True)
class ScanMemory:
    lock: threading.Lock
    taken_at: float
    measured: frozenset[ProcessKey]
    snapshot: ProcessSnapshot | None
    account_names: dict[int, str]


def new_scan_memory() -> ScanMemory:
    return ScanMemory(lock=threading.Lock(), taken_at=0.0, measured=frozenset(), snapshot=None, account_names={})


def runs_privileged() -> bool:
    if sys.platform == "win32":
        import ctypes

        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    return os.geteuid() == 0


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
        name = process.username()
        bare = name.rpartition("\\")[2].casefold()
        return name, bare == getpass.getuser().casefold(), bare in SYSTEM_ACCOUNT_NAMES
    account = process.uids().real
    if account not in account_names:
        # psutil asks the account database on every call, which is the slowest part of a reading; an account's name does not change while the server runs.
        account_names[account] = process.username()
    return account_names[account], account == os.getuid(), account < SYSTEM_ACCOUNT_LIMIT.get(sys.platform, 0)


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
    except psutil.NoSuchProcess:
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


# The server itself, what it runs inside (stopping that takes the server with it) and what it started.
def mark_server_family(rows: list[ProcessRow]) -> None:
    by_pid = {row["pid"]: row for row in rows}
    server = os.getpid()
    if server not in by_pid:
        return
    by_pid[server]["role"] = "server"
    seen = {server}
    ancestor = by_pid[server]["parent"]
    while ancestor > 1 and ancestor in by_pid and ancestor not in seen:
        seen.add(ancestor)
        by_pid[ancestor]["role"] = "server_parent"
        ancestor = by_pid[ancestor]["parent"]
    children: dict[int, list[int]] = {}
    for row in rows:
        children.setdefault(row["parent"], []).append(row["pid"])
    waiting = list(children.get(server, []))
    while waiting:
        pid = waiting.pop()
        if pid in seen:
            continue
        seen.add(pid)
        by_pid[pid]["role"] = "server_child"
        waiting.extend(children.get(pid, []))


# `fresh` asks for a new reading even when the last one is a moment old: after something was stopped, that one still lists it.
def read_processes(memory: ScanMemory, fresh: bool) -> ProcessSnapshot:
    with memory.lock:
        now = time.monotonic()
        if not fresh and memory.snapshot is not None and now - memory.taken_at < SNAPSHOT_REUSE_SECONDS:
            return memory.snapshot
        measurable = memory.snapshot is not None and now - memory.taken_at <= CPU_WINDOW_SECONDS
        machine_cpu = psutil.cpu_percent(interval=None)
        rows = [row for row in (read_row(process=process, account_names=memory.account_names) for process in psutil.process_iter()) if row is not None]
        # A processor figure only means something for a process that was also read last time, so the rest are left out until the next reading.
        measured = frozenset((row["pid"], row["started"]) for row in rows if row["cpu"] is not None)
        for row in rows:
            if not measurable or (row["pid"], row["started"]) not in memory.measured:
                row["cpu"] = None
        mark_server_family(rows)
        virtual = psutil.virtual_memory()
        snapshot: ProcessSnapshot = {
            "taken_at": time.time(),
            "user": getpass.getuser(),
            "privileged": runs_privileged(),
            "machine": {"cores": psutil.cpu_count() or 1, "cpu": machine_cpu if measurable else None, "memory_total": virtual.total, "memory_used": virtual.total - virtual.available},
            "processes": rows,
        }
        memory.taken_at = now
        memory.measured = measured
        memory.snapshot = snapshot
        return snapshot
