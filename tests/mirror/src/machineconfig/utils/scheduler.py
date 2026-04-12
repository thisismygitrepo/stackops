from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import sys
import types

import pytest

from machineconfig.utils import scheduler as scheduler_module


@dataclass(slots=True)
class StubLogger:
    traces: list[str] = field(default_factory=list)
    successes: list[str] = field(default_factory=list)
    debugs: list[str] = field(default_factory=list)
    infos: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    criticals: list[str] = field(default_factory=list)

    def trace(self, __message: str, *args: object, **kwargs: object) -> None:
        self.traces.append(__message)

    def success(self, __message: str, *args: object, **kwargs: object) -> None:
        self.successes.append(__message)

    def debug(self, __message: str, *args: object, **kwargs: object) -> None:
        self.debugs.append(__message)

    def info(self, __message: str, *args: object, **kwargs: object) -> None:
        self.infos.append(__message)

    def warning(self, __message: str, *args: object, **kwargs: object) -> None:
        self.warnings.append(__message)

    def error(self, __message: str, *args: object, **kwargs: object) -> None:
        self.errors.append(__message)

    def critical(self, __message: str, *args: object, **kwargs: object) -> None:
        self.criticals.append(__message)


def test_scheduler_run_records_summary_when_max_cycles_reached(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logger = StubLogger()
    routine_calls: list[int] = []
    sleep_calls: list[float] = []
    fake_time_values = iter(
        [
            0,
            0,
            10_000_000,
            20_000_000,
            30_000_000,
            40_000_000,
        ]
    )

    def fake_time_ns() -> int:
        return next(fake_time_values)

    def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    fake_accessories = types.ModuleType("machineconfig.utils.accessories")

    def fake_get_repr(value: object) -> str:
        return f"repr:{value!r}"

    fake_accessories.get_repr = fake_get_repr
    monkeypatch.setitem(sys.modules, "machineconfig.utils.accessories", fake_accessories)
    monkeypatch.setattr(scheduler_module.time, "time_ns", fake_time_ns)
    monkeypatch.setattr(scheduler_module.time, "sleep", fake_sleep)

    def routine(sched: scheduler_module.Scheduler) -> None:
        routine_calls.append(sched.cycle)

    sched = scheduler_module.Scheduler(
        routine=routine,
        wait_ms=100,
        logger=logger,
        sess_stats=lambda _sched: {"jobs": len(routine_calls)},
        max_cycles=1,
    )

    sched.run()

    assert routine_calls == [0]
    assert sleep_calls == [pytest.approx(0.09)]
    assert sched.cycle == 1
    assert len(sched.records) == 1
    assert sched.get_records_df() == [
        {
            "start": 0,
            "finish": 40,
            "duration": 40,
            "cycles": 1,
            "termination reason": "Reached maximum number of cycles (1)",
            "jobs": 1,
        }
    ]
    assert any("Scheduler has finished running a session" in message for message in logger.criticals)
    assert any("Logger history" in message for message in logger.criticals)


def test_cache_memory_reuses_value_until_it_expires() -> None:
    logger = StubLogger()
    source_calls: list[int] = []

    def source() -> int:
        source_calls.append(1)
        return len(source_calls)

    cache = scheduler_module.CacheMemory(
        source_func=source,
        expire=timedelta(days=1),
        logger=logger,
        name="numbers",
    )

    first = cache(fresh=False, tolerance_seconds=0)
    second = cache(fresh=False, tolerance_seconds=0)
    cache.time_produced = datetime.now() - timedelta(days=2)
    third = cache(fresh=False, tolerance_seconds=0)

    assert (first, second, third) == (1, 1, 2)
    assert source_calls == [1, 1]
    assert any("USING CACHE" in message for message in logger.warnings)
    assert any("CACHE STALE" in message for message in logger.warnings)


def test_cache_reads_existing_disk_value_before_calling_source(
    tmp_path: Path,
) -> None:
    logger = StubLogger()
    source_calls: list[str] = []
    save_calls: list[tuple[str, Path]] = []
    read_calls: list[Path] = []
    cache_path = tmp_path / "cache" / "value.bin"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text("placeholder", encoding="utf-8")

    def source() -> str:
        source_calls.append("source")
        return "fresh"

    def saver(value: str, path: Path) -> None:
        save_calls.append((value, path))

    def reader(path: Path) -> str:
        read_calls.append(path)
        return "from-disk"

    cache = scheduler_module.Cache(
        source_func=source,
        expire=timedelta(days=1),
        logger=logger,
        path=cache_path,
        saver=saver,
        reader=reader,
        name="disk-cache",
    )

    result = cache(fresh=False, tolerance_seconds=0)

    assert result == "from-disk"
    assert source_calls == []
    assert save_calls == []
    assert read_calls == [cache_path]


def test_cache_recovers_from_corrupt_disk_value_by_refreshing(
    tmp_path: Path,
) -> None:
    logger = StubLogger()
    source_calls: list[str] = []
    save_calls: list[tuple[str, Path]] = []
    cache_path = tmp_path / "cache" / "value.bin"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text("placeholder", encoding="utf-8")

    def source() -> str:
        source_calls.append("source")
        return "fresh"

    def saver(value: str, path: Path) -> None:
        save_calls.append((value, path))

    def reader(path: Path) -> str:
        raise ValueError(f"bad cache at {path}")

    cache = scheduler_module.Cache(
        source_func=source,
        expire=timedelta(days=1),
        logger=logger,
        path=cache_path,
        saver=saver,
        reader=reader,
        name="disk-cache",
    )

    result = cache(fresh=False, tolerance_seconds=0)

    assert result == "fresh"
    assert source_calls == ["source"]
    assert save_calls == [("fresh", cache_path)]
    assert any("CACHE ERROR" in message for message in logger.warnings)
