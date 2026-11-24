import os
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from typing import Final, TypedDict

import psutil

from stackops.scripts.python.helpers.helpers_webui.machine_processes_rows import ProcessRow, read_row

# Two pages asking at nearly the same moment share one reading, so each processor figure still covers a real stretch of time.
SNAPSHOT_REUSE_SECONDS: Final[float] = 1.0
# Processor use is what a process did since the reading before. Past this gap that says nothing about now, so the figures are left out once.
CPU_WINDOW_SECONDS: Final[float] = 20.0
FOREIGN_FIGURES_COMMAND: Final[tuple[str, ...]] = ("/bin/ps", "-o", "pid=,pcpu=,rss=,command=", "-p")
FOREIGN_FIGURES_SECONDS: Final[float] = 5.0

type ProcessKey = tuple[int, float]


class MachineLoad(TypedDict):
    cores: int
    cpu: float | None
    memory_total: int
    memory_used: int


class ProcessSnapshot(TypedDict):
    taken_at: float
    privileged: bool
    machine: MachineLoad
    processes: list[ProcessRow]


# What one reading leaves for the next: when it was taken, which processes it measured, and the reading itself for a page that asks a moment later.
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


# macOS lets only a process's owner or an administrator read its processor use, memory and command, which leaves out the system's own
# processes, often the busiest ones. `ps` is installed with the right to read them for everyone, so on macOS it fills those three in.
# Its processor figure is an average over the last few seconds, as the others are. Elsewhere psutil reads every process and this adds nothing.
def read_foreign_figures(pids: list[int]) -> dict[int, tuple[float, int, str]]:
    if sys.platform != "darwin" or len(pids) == 0:
        return {}
    listed = subprocess.run(
        [*FOREIGN_FIGURES_COMMAND, ",".join(str(pid) for pid in pids)], capture_output=True, text=True, timeout=FOREIGN_FIGURES_SECONDS, check=False, env={"LC_ALL": "C"}
    )
    figures: dict[int, tuple[float, int, str]] = {}
    for line in listed.stdout.splitlines():
        fields = line.split(None, 3)
        if len(fields) == 4:
            figures[int(fields[0])] = (float(fields[1]), int(fields[2]) * 1024, fields[3])
    return figures


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
        foreign = [row for row in rows if not row["readable"] and row["status"] != psutil.STATUS_ZOMBIE]
        figures = read_foreign_figures([row["pid"] for row in foreign])
        for row in foreign:
            if row["pid"] in figures:
                row["cpu"], row["memory"], row["command"] = figures[row["pid"]]
        mark_server_family(rows)
        virtual = psutil.virtual_memory()
        snapshot: ProcessSnapshot = {
            "taken_at": time.time(),
            "privileged": runs_privileged(),
            "machine": {"cores": psutil.cpu_count() or 1, "cpu": machine_cpu if measurable else None, "memory_total": virtual.total, "memory_used": virtual.total - virtual.available},
            "processes": rows,
        }
        memory.taken_at = now
        memory.measured = measured
        memory.snapshot = snapshot
        return snapshot
