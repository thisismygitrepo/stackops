from dataclasses import dataclass

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
