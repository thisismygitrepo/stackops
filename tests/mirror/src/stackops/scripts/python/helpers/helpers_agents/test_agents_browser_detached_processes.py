from dataclasses import dataclass
from pathlib import Path

import psutil
import pytest

from stackops.scripts.python.helpers.helpers_agents import agents_browser_detached_processes


@dataclass(frozen=True)
class FakeProcess:
    pid: int
    process_name: str | Exception

    def name(self) -> str:
        if isinstance(self.process_name, Exception):
            raise self.process_name
        return self.process_name


@dataclass
class FakeTrackedProcess:
    pid: int
    created_at: float
    command: tuple[str, ...]
    terminated: bool = False
    wait_timeout: float | None = None

    def create_time(self) -> float:
        return self.created_at

    def is_running(self) -> bool:
        return True

    def status(self) -> str:
        return psutil.STATUS_RUNNING

    def cmdline(self) -> list[str]:
        return list(self.command)

    def terminate(self) -> None:
        self.terminated = True

    def wait(self, timeout: float) -> None:
        self.wait_timeout = timeout


@pytest.mark.parametrize(
    ("system_name", "parent_name", "helper_name"),
    (
        ("Windows", "CHROME.EXE", "Chrome Helper (Renderer)"),
        ("Darwin", "Google Chrome", "GOOGLE CHROME HELPER (Renderer)"),
        ("Linux", "google-chrome-stable", "Google-Chrome-Stable Helper (Renderer)"),
    ),
)
def test_find_chrome_process_ids_normalizes_platform_names_and_filters_unrelated_processes(
    monkeypatch: pytest.MonkeyPatch, system_name: str, parent_name: str, helper_name: str
) -> None:
    processes = (
        FakeProcess(pid=91, process_name="chromedriver"),
        FakeProcess(pid=24, process_name=helper_name),
        FakeProcess(pid=72, process_name="Brave Browser Helper (Renderer)"),
        FakeProcess(pid=8, process_name=parent_name),
        FakeProcess(pid=13, process_name=psutil.AccessDenied(pid=13)),
        FakeProcess(pid=50, process_name="chrome_crashpad_handler"),
    )

    monkeypatch.setattr(agents_browser_detached_processes.platform, "system", lambda: system_name)
    monkeypatch.setattr(agents_browser_detached_processes.psutil, "process_iter", lambda: iter(processes))

    assert agents_browser_detached_processes.find_browser_process_ids(browser="chrome") == (8, 24)


def test_find_brave_process_ids_matches_darwin_parent_and_helper_only(monkeypatch: pytest.MonkeyPatch) -> None:
    processes = (
        FakeProcess(pid=41, process_name="Google Chrome Helper (Renderer)"),
        FakeProcess(pid=19, process_name="BRAVE BROWSER HELPER (GPU)"),
        FakeProcess(pid=7, process_name="Brave Browser"),
        FakeProcess(pid=3, process_name="brave_crashpad_handler"),
    )

    monkeypatch.setattr(agents_browser_detached_processes.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(agents_browser_detached_processes.psutil, "process_iter", lambda: iter(processes))

    assert agents_browser_detached_processes.find_browser_process_ids(browser="brave") == (7, 19)


def test_terminate_browser_launch_process_revalidates_and_terminates_exact_handoff(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    profile_path = tmp_path.joinpath("browsers-profiles", "chrome", "p1")
    profile_path.mkdir(parents=True)
    process = FakeTrackedProcess(pid=202, created_at=2.02, command=("chrome.exe", "--remote-debugging-port=60001", f"--user-data-dir={profile_path}"))
    monkeypatch.setattr(agents_browser_detached_processes, "find_browser_process_id", lambda **_kwargs: process.pid)
    monkeypatch.setattr(agents_browser_detached_processes.psutil, "Process", lambda process_id: process)

    agents_browser_detached_processes.terminate_browser_launch_process(
        browser="chrome", browser_port=60001, profile_path=profile_path, process_id=101, process_created_at=1.01, process_label="chrome browser"
    )

    assert process.terminated is True
    assert process.wait_timeout == agents_browser_detached_processes.BROWSER_PROCESS_TERMINATION_TIMEOUT_SECONDS


def test_terminate_browser_launch_process_rejects_fallback_that_no_longer_matches_profile(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    profile_path = tmp_path.joinpath("browsers-profiles", "chrome", "p1")
    other_profile_path = tmp_path.joinpath("browsers-profiles", "chrome", "personal")
    profile_path.mkdir(parents=True)
    other_profile_path.mkdir()
    process = FakeTrackedProcess(
        pid=202, created_at=2.02, command=("chrome.exe", "--remote-debugging-port=60001", f"--user-data-dir={other_profile_path}")
    )
    monkeypatch.setattr(agents_browser_detached_processes, "find_browser_process_id", lambda **_kwargs: process.pid)
    monkeypatch.setattr(agents_browser_detached_processes.psutil, "Process", lambda process_id: process)

    agents_browser_detached_processes.terminate_browser_launch_process(
        browser="chrome", browser_port=60001, profile_path=profile_path, process_id=101, process_created_at=1.01, process_label="chrome browser"
    )

    assert process.terminated is False
    assert process.wait_timeout is None
