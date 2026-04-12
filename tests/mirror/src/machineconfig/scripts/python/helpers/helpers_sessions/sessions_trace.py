from __future__ import annotations

from dataclasses import dataclass

import pytest
import typer
from rich.panel import Panel

from machineconfig.scripts.python.helpers.helpers_sessions import sessions_trace as subject


@dataclass(slots=True)
class EstimateSnapshot:
    criterion_satisfied: bool
    total_targets: int
    matched_targets: int


@dataclass(slots=True)
class LoopSnapshot:
    criterion_satisfied: bool


def test_duration_estimation_and_validation() -> None:
    assert subject._format_duration(None) == "unknown"
    assert subject._format_duration(65.2) == "01:05"
    assert subject._format_duration(3661.0) == "01:01:01"
    assert (
        subject._estimate_remaining_seconds(
            snapshot=EstimateSnapshot(criterion_satisfied=False, total_targets=4, matched_targets=2), elapsed_seconds=10.0
        )
        == 10.0
    )
    assert (
        subject._estimate_remaining_seconds(
            snapshot=EstimateSnapshot(criterion_satisfied=True, total_targets=4, matched_targets=1), elapsed_seconds=10.0
        )
        == 0.0
    )
    assert (
        subject._estimate_remaining_seconds(
            snapshot=EstimateSnapshot(criterion_satisfied=False, total_targets=0, matched_targets=0), elapsed_seconds=10.0
        )
        is None
    )

    with pytest.raises(typer.BadParameter, match="greater than 0"):
        subject._validate_trace_options(until="idle-shell", every_seconds=0.0, exit_code=None)

    with pytest.raises(typer.BadParameter, match="required when `--until exit-code`"):
        subject._validate_trace_options(until="exit-code", every_seconds=1.0, exit_code=None)

    with pytest.raises(typer.BadParameter, match="can only be used together"):
        subject._validate_trace_options(until="all-exited", every_seconds=1.0, exit_code=7)


def test_trace_session_for_backend_polls_until_snapshot_is_satisfied(monkeypatch: pytest.MonkeyPatch) -> None:
    sleep_calls: list[float] = []
    live_instances: list[FakeLive] = []
    console_instances: list[FakeConsole] = []
    loader_calls: list[tuple[str, str, int | None]] = []
    snapshots = iter([LoopSnapshot(False), LoopSnapshot(True)])
    moments = iter([10.0, 11.0, 11.5, 12.0, 12.5])

    class FakeConsole:
        def __init__(self) -> None:
            self.printed: list[object] = []
            console_instances.append(self)

        def print(self, renderable: object) -> None:
            self.printed.append(renderable)

    class FakeLive:
        def __init__(self, renderable: object, console: FakeConsole, refresh_per_second: int, transient: bool) -> None:
            assert refresh_per_second == 8
            assert transient is False
            self.console = console
            self.updates: list[object] = [renderable]
            live_instances.append(self)

        def __enter__(self) -> FakeLive:
            return self

        def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, traceback: object) -> None:
            return None

        def update(self, renderable: object) -> None:
            self.updates.append(renderable)

    def fake_loader(session_name: str, until: str, exit_code: int | None) -> LoopSnapshot:
        loader_calls.append((session_name, until, exit_code))
        return next(snapshots)

    monkeypatch.setitem(subject._TRACE_LOADERS, "tmux", fake_loader)
    monkeypatch.setattr(subject, "build_missing_snapshot", lambda session_name, until, session_error: LoopSnapshot(False))
    monkeypatch.setattr(
        subject,
        "_build_trace_renderable",
        lambda snapshot, until, exit_code, attempt, elapsed_seconds, next_poll_seconds, checked_at_text: (
            attempt,
            round(next_poll_seconds, 2),
            snapshot.criterion_satisfied,
            checked_at_text,
        ),
    )
    monkeypatch.setattr(subject, "_checked_at_text", lambda: "NOW")
    monkeypatch.setattr(subject, "Console", FakeConsole)
    monkeypatch.setattr(subject, "Live", FakeLive)
    monkeypatch.setattr(subject, "sleep", lambda seconds: sleep_calls.append(seconds))
    monkeypatch.setattr(subject, "monotonic", lambda: next(moments))

    subject.trace_session_for_backend(backend="tmux", session_name="session-1", until="idle-shell", every_seconds=0.5, exit_code=None)

    assert loader_calls == [("session-1", "idle-shell", None), ("session-1", "idle-shell", None)]
    assert sleep_calls == [0.5]
    assert len(live_instances) == 1
    assert live_instances[0].updates == [(0, 0.0, False, "NOW"), (1, 0.5, False, "NOW"), (1, 0.0, False, "NOW"), (2, 0.5, True, "NOW")]
    assert len(console_instances) == 1
    assert len(console_instances[0].printed) == 1
    assert isinstance(console_instances[0].printed[0], Panel)
    assert console_instances[0].printed[0].title == "Complete"


def test_trace_session_for_backend_converts_not_implemented_loader_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeConsole:
        def print(self, renderable: object) -> None:
            raise AssertionError(f"unexpected print: {renderable}")

    class FakeLive:
        def __init__(self, renderable: object, console: FakeConsole, refresh_per_second: int, transient: bool) -> None:
            self.renderable = renderable

        def __enter__(self) -> FakeLive:
            return self

        def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, traceback: object) -> None:
            return None

        def update(self, renderable: object) -> None:
            raise AssertionError(f"unexpected update: {renderable}")

    def fake_loader(session_name: str, until: str, exit_code: int | None) -> LoopSnapshot:
        raise NotImplementedError("backend missing")

    monkeypatch.setitem(subject._TRACE_LOADERS, "tmux", fake_loader)
    monkeypatch.setattr(subject, "build_missing_snapshot", lambda session_name, until, session_error: LoopSnapshot(False))
    monkeypatch.setattr(subject, "_build_trace_renderable", lambda *args, **kwargs: "renderable")
    monkeypatch.setattr(subject, "_checked_at_text", lambda: "NOW")
    monkeypatch.setattr(subject, "Console", FakeConsole)
    monkeypatch.setattr(subject, "Live", FakeLive)
    monkeypatch.setattr(subject, "monotonic", lambda: 0.0)

    with pytest.raises(typer.BadParameter, match="backend missing"):
        subject.trace_session_for_backend(backend="tmux", session_name="session-1", until="idle-shell", every_seconds=1.0, exit_code=None)
