from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess

import pytest

from machineconfig.cluster.sessions_managers.zellij.zellij_utils import zellij_local_helper as subject
from machineconfig.utils.schemas.layouts.layout_types import LayoutConfig


def _make_layout_config(command: str) -> LayoutConfig:
    return {"layoutName": "Local", "layoutTabs": [{"tabName": "worker", "startDir": "/repo", "command": command}]}


@dataclass(slots=True)
class FakeMemoryInfo:
    rss: int


@dataclass(slots=True)
class FakeChildProcess:
    child_name: str
    child_cmdline: list[str]
    running: bool = True

    def is_running(self) -> bool:
        return self.running

    def name(self) -> str:
        return self.child_name

    def cmdline(self) -> list[str]:
        return self.child_cmdline


class FakeTrackedProcess:
    def __init__(
        self, pid: int, status: str, *, children: list[FakeChildProcess] | None = None, running: bool = True, rss: int = 0, created_at: float = 10.0
    ) -> None:
        self.pid = pid
        self._status = status
        self._children = [] if children is None else children
        self._running = running
        self._rss = rss
        self._created_at = created_at

    def status(self) -> str:
        return self._status

    def memory_info(self) -> FakeMemoryInfo:
        return FakeMemoryInfo(rss=self._rss)

    def children(self, recursive: bool) -> list[FakeChildProcess]:
        return list(self._children)

    def is_running(self) -> bool:
        return self._running

    def create_time(self) -> float:
        return self._created_at


@dataclass(slots=True)
class FakeIterProcess:
    info: dict[str, object]


def test_normalize_cli_token_expands_home_and_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCFG_TOKEN", "expanded")

    normalized = subject._normalize_cli_token("'~/bin/$MCFG_TOKEN'")

    assert normalized == str(Path.home().joinpath("bin", "expanded"))


def test_check_command_status_matches_live_direct_process(monkeypatch: pytest.MonkeyPatch) -> None:
    tracked = {101: FakeTrackedProcess(101, "sleeping", rss=50 * 1024 * 1024)}
    iter_processes = [
        FakeIterProcess(
            {
                "pid": 101,
                "name": "python",
                "cmdline": ["python", "worker.py", "--port", "9000"],
                "status": "sleeping",
                "ppid": 1,
                "create_time": 10.0,
                "memory_info": None,
            }
        )
    ]
    monkeypatch.setattr(subject.psutil, "process_iter", lambda _attrs: iter_processes)
    monkeypatch.setattr(subject.psutil, "Process", lambda pid: tracked[pid])

    result = subject.check_command_status("worker", _make_layout_config("python worker.py --port 9000"))

    assert result["status"] == "running"
    assert result["running"] is True
    assert result["processes"][0]["pid"] == 101
    assert result["processes"][0]["memory_mb"] == 50.0


def test_check_command_status_filters_idle_wrapper_shells(monkeypatch: pytest.MonkeyPatch) -> None:
    tracked = {202: FakeTrackedProcess(202, "sleeping", children=[])}
    iter_processes = [
        FakeIterProcess(
            {
                "pid": 202,
                "name": "bash",
                "cmdline": ["bash", "/tmp/run.sh"],
                "status": "sleeping",
                "ppid": 1,
                "create_time": 10.0,
                "memory_info": None,
            }
        )
    ]
    monkeypatch.setattr(subject.psutil, "process_iter", lambda _attrs: iter_processes)
    monkeypatch.setattr(subject.psutil, "Process", lambda pid: tracked[pid])

    result = subject.check_command_status("worker", _make_layout_config("bash /tmp/run.sh"))

    assert result["status"] == "not_running"
    assert result["processes"] == []


def test_check_zellij_session_status_handles_missing_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError

    monkeypatch.setattr(subject.subprocess, "run", fake_run)

    result = subject.check_zellij_session_status("main-session")

    assert result == {
        "zellij_running": False,
        "session_exists": False,
        "session_name": "main-session",
        "all_sessions": [],
        "error": "Zellij not found in PATH",
    }


def test_get_layout_preview_uses_default_template() -> None:
    preview = subject.get_layout_preview(_make_layout_config("python worker.py"), layout_template=None)

    assert preview.startswith("layout {")
    assert 'tab name="worker" cwd="/repo"' in preview
    assert 'pane command="python"' in preview
    assert preview.endswith("\n}\n")
