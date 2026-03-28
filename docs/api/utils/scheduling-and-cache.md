# Scheduling and Cache

The scheduling layer provides two related capabilities:

- recurring execution through `Scheduler`
- reuse of expensive results through `CacheMemory` and `Cache`

These APIs are especially useful for bots, polling loops, stream processors, background routines, and "fetch once, reuse many times" application logic.

---

## Core classes

| API | Role |
| --- | --- |
| `Scheduler` | Runs a routine repeatedly with a fixed wait interval and session-level record keeping |
| `CacheMemory[T]` | Stores values in memory and refreshes them on demand or after expiry |
| `Cache[T]` | Adds a disk-backed cache file on top of the same refresh semantics |

---

## Scheduler lifecycle

A `Scheduler` instance is defined by:

- a `routine` that receives the current scheduler
- a `wait_ms` interval between cycles
- a logger
- optional session stats and exception handling hooks

While it runs, the scheduler tracks:

- the current cycle count
- session start time
- session history records
- a structured summary when a session ends

That makes it more than a thin `while True` loop: it provides lifecycle bookkeeping that other helpers can build on.

---

## Cache models

| Cache type | Backing store | Best for |
| --- | --- | --- |
| `CacheMemory` | In-memory attribute on the wrapper object | Fast repeated access inside a single process |
| `Cache` | In-memory access plus persisted cache file | Reusing expensive results across runs |

Both cache wrappers use the same calling convention:

```python
value = cache_wrapper(fresh=False, tolerance_seconds=0)
```

`fresh=True` forces stricter refresh behavior, while `tolerance_seconds` lets callers define how much staleness is acceptable for that specific call.

---

## Example usage

```python
from datetime import timedelta

from machineconfig.logger import get_logger
from machineconfig.utils.scheduler import CacheMemory, Scheduler

logger = get_logger("market-poller")


def fetch_snapshot() -> dict[str, float]:
    return {"btc": 100_000.0}


snapshot_cache = CacheMemory(
    source_func=fetch_snapshot,
    expire=timedelta(seconds=30),
    logger=logger,
)


def routine(scheduler: Scheduler) -> None:
    snapshot = snapshot_cache(fresh=False, tolerance_seconds=0)
    logger.info("cycle=%s snapshot=%s", scheduler.cycle, snapshot)


Scheduler(
    routine=routine,
    wait_ms=5_000,
    logger=logger,
    max_cycles=5,
).run()
```

---

## Decorator form

Both cache types also expose `as_decorator(...)`, which is useful when the expensive function already exists and you want to wrap it once at definition time.

```python
from datetime import timedelta
from pathlib import Path

from machineconfig.logger import get_logger
from machineconfig.utils.scheduler import Cache

logger = get_logger("symbols")


@Cache.as_decorator(
    expire=timedelta(minutes=10),
    logger=logger,
    path=Path("tmp/symbols.pkl"),
)
def load_symbols() -> list[str]:
    return ["BTCUSDT", "ETHUSDT"]
```

---

## API reference

::: machineconfig.utils.scheduler
    options:
      show_root_heading: true
      show_source: false
      members_order: source
