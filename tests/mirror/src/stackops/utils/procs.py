from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import pytest

import stackops.utils.procs as procs


@dataclass(frozen=True, slots=True)
class _FakeOpenFile:
    path: str


@dataclass(slots=True)
class _IterProcess:
    pid: int
    process_name: str
    open_file_paths: tuple[str, ...]
    killed: bool = False

    def open_files(self) -> list[_FakeOpenFile]:
        return [_FakeOpenFile(path=item) for item in self.open_file_paths]

    def name(self) -> str:
        return self.process_name

    def kill(self) -> None:
        self.killed = True


@dataclass(frozen=True, slots=True)
class _DeniedProcess:
    pid: int

    def open_files(self) -> list[_FakeOpenFile]:
        raise procs.psutil.AccessDenied()


@dataclass(slots=True)
class _ProcessHandle:
    pid: int
    killed_pids: set[int]

    def name(self) -> str:
        return f"pid-{self.pid}"

    def create_time(self) -> float:
        return (datetime.now() - timedelta(minutes=5)).timestamp()

    def kill(self) -> None:
        self.killed_pids.add(self.pid)


def _fake_print(*_args: object, **_kwargs: object) -> None:
    return None


def _fake_rule(*_args: object, **_kwargs: object) -> None:
    return None


def _build_process_info(
    *,
    pid: int,
    name: str,
    command: str,
    ports: list[int],
) -> procs.ProcessInfo:
    return {
        "pid": pid,
        "name": name,
        "username": "alex",
        "cpu_percent": 1.5,
        "memory_usage_mb": 32.0,
        "status": "running",
        "create_time": datetime(2024, 1, 1, 12, 0, 0),
        "command": command,
        "ports": ports,
    }


def test_get_processes_accessing_file_returns_matching_processes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    processes: list[object] = [
        _IterProcess(pid=1, process_name="alpha", open_file_paths=("/tmp/target.log", "/tmp/other.log")),
        _DeniedProcess(pid=2),
        _IterProcess(pid=3, process_name="beta", open_file_paths=("/tmp/nope.log",)),
    ]

    def fake_process_iter() -> list[object]:
        return processes

    monkeypatch.setattr(procs.psutil, "process_iter", fake_process_iter)
    monkeypatch.setattr(procs.console, "print", _fake_print)

    result = procs.get_processes_accessing_file("target.log")

    assert result == [{"pid": 1, "files": ["/tmp/target.log"]}]


def test_kill_process_terminates_matching_processes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    alpha = _IterProcess(pid=1, process_name="alpha", open_file_paths=())
    beta = _IterProcess(pid=2, process_name="beta", open_file_paths=())

    def fake_process_iter() -> list[_IterProcess]:
        return [alpha, beta]

    monkeypatch.setattr(procs.psutil, "process_iter", fake_process_iter)
    monkeypatch.setattr(procs.console, "print", _fake_print)
    monkeypatch.setattr(procs.console, "rule", _fake_rule)

    procs.kill_process("alpha")

    assert alpha.killed is True
    assert beta.killed is False


def test_process_manager_search_value_and_table_formatting() -> None:
    manager = procs.ProcessManager.__new__(procs.ProcessManager)
    manager.data = [
        _build_process_info(pid=1, name="alpha", command="alpha --serve", ports=[80, 443]),
    ]

    assert manager._search_value(manager.data[0], "ports") == "80,443"

    formatted = manager._format_process_table()

    assert "Memory(MB)" in formatted
    assert "alpha --serve" in formatted


def test_process_manager_kill_requires_target() -> None:
    manager = procs.ProcessManager.__new__(procs.ProcessManager)
    manager.data = []

    with pytest.raises(ValueError):
        manager.kill()


def test_process_manager_kill_targets_names_pids_and_commands(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = procs.ProcessManager.__new__(procs.ProcessManager)
    manager.data = [
        _build_process_info(pid=1, name="alpha", command="alpha --serve", ports=[]),
        _build_process_info(pid=2, name="beta", command="beta worker", ports=[]),
    ]
    killed_pids: set[int] = set()

    def fake_process_factory(pid: int) -> _ProcessHandle:
        return _ProcessHandle(pid=pid, killed_pids=killed_pids)

    monkeypatch.setattr(procs.psutil, "Process", fake_process_factory)
    monkeypatch.setattr(procs.console, "print", _fake_print)

    manager.kill(names=["alpha"], pids=[7], commands=["beta"])

    assert killed_pids == {1, 2, 7}
