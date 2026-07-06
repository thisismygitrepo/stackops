import time
from collections.abc import Callable
from dataclasses import replace
from types import TracebackType

import pytest
from rich import console as rich_console
from rich import live as rich_live

from stackops.scripts.python.helpers.helpers_sessions import (
    session_trace_kill,
    session_trace_runner,
    sessions_trace,
)
from stackops.scripts.python.helpers.helpers_sessions.session_trace_models import (
    TraceSnapshot,
    TraceUntil,
    build_missing_snapshot,
)


class _FakeConsole:
    def __init__(self) -> None:
        self.printed: list[object] = []

    def print(self, renderable: object) -> None:
        self.printed.append(renderable)


class _FakeLive:
    def __init__(
        self,
        renderable: object,
        *,
        console: object,
        refresh_per_second: int,
        transient: bool,
    ) -> None:
        _ = console, refresh_per_second, transient
        self.updates: list[object] = [renderable]

    def __enter__(self) -> "_FakeLive":
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        _ = exception_type, exception, traceback
        return False

    def update(self, renderable: object) -> None:
        self.updates.append(renderable)


def test_trace_sessions_for_backend_requires_all_sessions_to_satisfy_the_criterion_in_one_poll(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_names = ["alpha", "beta"]
    criterion_by_poll = (
        {"alpha": True, "beta": False},
        {"alpha": False, "beta": True},
        {"alpha": True, "beta": True},
    )
    loader_calls: list[str] = []
    sleep_calls: list[float] = []

    def fake_snapshot_loader(session_name: str, until: TraceUntil, expected_exit_code: int | None) -> TraceSnapshot:
        assert until == "idle-shell"
        assert expected_exit_code is None
        poll_index = len(loader_calls) // len(session_names)
        loader_calls.append(session_name)
        return replace(
            build_missing_snapshot(
                session_name=session_name,
                until=until,
                session_error=None,
            ),
            criterion_satisfied=criterion_by_poll[poll_index][session_name],
        )

    def fake_get_trace_loader(
        backend: sessions_trace.TraceBackend,
    ) -> Callable[[str, TraceUntil, int | None], TraceSnapshot]:
        assert backend == "tmux"
        return fake_snapshot_loader

    def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr(sessions_trace, "_get_trace_loader", fake_get_trace_loader)
    monkeypatch.setattr(rich_console, "Console", _FakeConsole)
    monkeypatch.setattr(rich_live, "Live", _FakeLive)
    monkeypatch.setattr(time, "sleep", fake_sleep)

    sessions_trace.trace_sessions_for_backend(
        backend="tmux",
        session_names=session_names,
        until="idle-shell",
        every_seconds=2.5,
        exit_code=None,
        kill=False,
    )

    assert loader_calls == ["alpha", "beta", "alpha", "beta", "alpha", "beta"]
    assert sleep_calls == [1.0, 1.0, 0.5, 1.0, 1.0, 0.5]


def test_trace_kill_finalizes_sessions_independently_and_stops_polling_them(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    criterion_by_session = {
        "alpha": iter((True,)),
        "beta": iter((False, True)),
    }
    loader_calls: list[str] = []
    executed_commands: list[tuple[str, ...]] = []
    sleep_calls: list[float] = []

    def fake_snapshot_loader(session_name: str, until: TraceUntil, expected_exit_code: int | None) -> TraceSnapshot:
        assert until == "all-exited"
        assert expected_exit_code is None
        loader_calls.append(session_name)
        return replace(
            build_missing_snapshot(
                session_name=session_name,
                until=until,
                session_error=None,
            ),
            session_exists=True,
            criterion_satisfied=next(criterion_by_session[session_name]),
        )

    def fake_get_trace_loader(
        backend: sessions_trace.TraceBackend,
    ) -> Callable[[str, TraceUntil, int | None], TraceSnapshot]:
        assert backend == "tmux"
        return fake_snapshot_loader

    def fake_execute_trace_kill_plan(plan: session_trace_kill.TraceKillPlan) -> None:
        executed_commands.extend(command.argv for command in plan.commands)

    def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr(sessions_trace, "_get_trace_loader", fake_get_trace_loader)
    monkeypatch.setattr(session_trace_runner, "execute_trace_kill_plan", fake_execute_trace_kill_plan)
    monkeypatch.setattr(rich_console, "Console", _FakeConsole)
    monkeypatch.setattr(rich_live, "Live", _FakeLive)
    monkeypatch.setattr(time, "sleep", fake_sleep)

    sessions_trace.trace_sessions_for_backend(
        backend="tmux",
        session_names=["alpha", "beta"],
        until="all-exited",
        every_seconds=2.5,
        exit_code=None,
        kill=True,
    )

    assert loader_calls == ["alpha", "beta", "beta"]
    assert executed_commands == [
        ("tmux", "kill-session", "-t", "alpha"),
        ("tmux", "kill-session", "-t", "beta"),
    ]
    assert sleep_calls == [1.0, 1.0, 0.5]
