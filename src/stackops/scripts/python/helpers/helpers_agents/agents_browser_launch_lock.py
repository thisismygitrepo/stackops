from collections.abc import Iterator
from contextlib import contextmanager
import os

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import BROWSER_LAUNCH_LOCK_PATH


@contextmanager
def browser_launch_lock() -> Iterator[None]:
    BROWSER_LAUNCH_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with BROWSER_LAUNCH_LOCK_PATH.open("a+b") as lock_file:
        if os.name == "nt":
            import msvcrt

            if lock_file.tell() == 0:
                lock_file.write(b"\0")
                lock_file.flush()
            lock_file.seek(0)
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            return

        import fcntl

        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
