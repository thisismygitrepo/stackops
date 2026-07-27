from datetime import datetime
from unittest.mock import Mock

import pytest
from typer.testing import CliRunner

from stackops.scripts.python.helpers.helpers_utils import processes
from stackops.scripts.python.helpers.helpers_utils.machine_utils_app import get_app
from stackops.scripts.python.helpers.helpers_utils.process_models import (
    IntegerProcessSelector,
    MinimumProcessSelector,
    ProcessInfo,
    ProcessSelector,
    SearchField,
    TextProcessSelector,
)


type SelectorCase = tuple[list[str], ProcessSelector]

SELECTOR_CASES: list[SelectorCase] = [
    (["--command", "UVICORN"], TextProcessSelector(field="command", value="UVICORN")),
    (["-p", "9221"], IntegerProcessSelector(field="ports", value=9221)),
    (["--name", "uvicorn"], TextProcessSelector(field="name", value="uvicorn")),
    (["-P", "101"], IntegerProcessSelector(field="pid", value=101)),
    (["--username", "alex"], TextProcessSelector(field="username", value="alex")),
    (["--status", "sleeping"], TextProcessSelector(field="status", value="sleeping")),
    (["--memory", "100"], MinimumProcessSelector(field="memory", value=100.0)),
    (["-C", "10"], MinimumProcessSelector(field="cpu", value=10.0)),
]


def _process_info(
    *,
    command: str,
    pid: int,
    name: str,
    username: str,
    status: str,
    memory_usage_mb: float,
    cpu_percent: float,
    ports: list[int],
) -> ProcessInfo:
    return {
        "command": command,
        "pid": pid,
        "name": name,
        "username": username,
        "cpu_percent": cpu_percent,
        "memory_usage_mb": memory_usage_mb,
        "status": status,
        "create_time": datetime(2026, 1, 1),
        "ports": ports,
    }


@pytest.mark.parametrize(("arguments", "expected_selector"), SELECTOR_CASES)
def test_direct_selector_options_are_forwarded(
    arguments: list[str],
    expected_selector: ProcessSelector,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[SearchField, ProcessSelector | None, bool]] = []

    class StubProcessManager:
        def choose_and_kill(self, search_by: SearchField, selector: ProcessSelector | None, kill_all_matches: bool) -> None:
            calls.append((search_by, selector, kill_all_matches))

    monkeypatch.setattr(processes, "ProcessManager", StubProcessManager)

    result = CliRunner().invoke(get_app(), ["k", *arguments, "--yes"])

    assert result.exit_code == 0
    assert calls == [(expected_selector.field, expected_selector, True)]


def test_direct_selector_without_yes_remains_interactive(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[SearchField, ProcessSelector | None, bool]] = []

    class StubProcessManager:
        def choose_and_kill(self, search_by: SearchField, selector: ProcessSelector | None, kill_all_matches: bool) -> None:
            calls.append((search_by, selector, kill_all_matches))

    monkeypatch.setattr(processes, "ProcessManager", StubProcessManager)

    result = CliRunner().invoke(get_app(), ["k", "--port", "9221"])

    expected_selector = IntegerProcessSelector(field="ports", value=9221)
    assert result.exit_code == 0
    assert calls == [("ports", expected_selector, False)]


@pytest.mark.parametrize("selector", [selector for _arguments, selector in SELECTOR_CASES])
def test_yes_kills_every_process_matching_selector(selector: ProcessSelector, monkeypatch: pytest.MonkeyPatch) -> None:
    manager = processes.ProcessManager.__new__(processes.ProcessManager)
    manager.data = [
        _process_info(
            command="uvicorn app:server",
            pid=101,
            name="uvicorn",
            username="alex",
            status="sleeping",
            memory_usage_mb=150.0,
            cpu_percent=30.0,
            ports=[9221],
        ),
        _process_info(
            command="python worker.py",
            pid=202,
            name="python",
            username="ci",
            status="running",
            memory_usage_mb=90.0,
            cpu_percent=5.0,
            ports=[8080],
        ),
    ]
    kill_mock = Mock()
    monkeypatch.setattr(manager, "kill", kill_mock)

    manager.choose_and_kill(search_by=selector.field, selector=selector, kill_all_matches=True)

    kill_mock.assert_called_once_with(pids=[101])


def test_yes_requires_a_direct_selector() -> None:
    result = CliRunner().invoke(get_app(), ["k", "--yes"])

    assert result.exit_code == 2
    assert "--yes requires a direct process selector" in result.output


def test_multiple_direct_selectors_are_rejected() -> None:
    result = CliRunner().invoke(get_app(), ["k", "--port", "9221", "--pid", "101"])

    assert result.exit_code == 2
    assert "Pass exactly one direct process selector" in result.output


def test_kill_process_help_lists_every_direct_selector() -> None:
    result = CliRunner().invoke(get_app(), ["k", "--help"], terminal_width=200)

    assert result.exit_code == 0
    for long_option, short_option in [
        ("--command", "-c"),
        ("--port", "-p"),
        ("--name", "-n"),
        ("--pid", "-P"),
        ("--username", "-u"),
        ("--status", "-s"),
        ("--memory", "-m"),
        ("--cpu", "-C"),
        ("--yes", "-y"),
    ]:
        assert long_option in result.output
        assert short_option in result.output
