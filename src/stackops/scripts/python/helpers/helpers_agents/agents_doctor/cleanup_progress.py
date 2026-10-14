import logging
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from rich.console import Console
from rich.filesize import decimal
from rich.progress import Progress, SpinnerColumn, TaskID, TextColumn, TimeElapsedColumn
from rich.table import Column


logger = logging.getLogger("stackops.depoison.progress")
logger.propagate = False


@dataclass(frozen=True)
class CleanupTargetProgress:
    path: Path
    index: int
    total: int


@dataclass(frozen=True)
class CleanupScanProgress:
    path: Path
    action: Literal["Inspecting", "Listing", "Reading", "Read"]
    files: int
    bytes_read: int
    file_size: int | None


class _CleanupProgressHandler(logging.Handler):
    def __init__(self, *, progress: Progress, task_id: TaskID) -> None:
        super().__init__(level=logging.INFO)
        self.progress = progress
        self.task_id = task_id
        self.target: CleanupTargetProgress | None = None

    def emit(self, record: logging.LogRecord) -> None:
        event = record.msg
        if isinstance(event, CleanupTargetProgress):
            self.target = event
        elif not isinstance(event, CleanupScanProgress):
            return
        lines = ["Building reset plan..."]
        if self.target is not None:
            lines[0] = f"""Building reset plan · target {self.target.index:,}/{self.target.total:,}"""
            lines.append(str(self.target.path))
        if isinstance(event, CleanupScanProgress):
            current = event.path.relative_to(self.target.path) if self.target is not None else event.path
            detail = f"""{event.action} {current}"""
            if event.file_size is not None:
                detail += f""" · {decimal(event.file_size)}"""
            lines.extend((detail, f"""This target: {event.files:,} files read · {decimal(event.bytes_read)}"""))
        self.progress.update(self.task_id, description="\n".join(lines))


@contextmanager
def show_cleanup_progress(*, console: Console) -> Iterator[None]:
    progress = Progress(
        SpinnerColumn(),
        TimeElapsedColumn(),
        TextColumn("{task.description}", markup=False, table_column=Column(ratio=1, overflow="fold")),
        console=console, auto_refresh=True, transient=True, expand=True,
    )
    task_id = progress.add_task("Building reset plan...", total=None)
    handler = _CleanupProgressHandler(progress=progress, task_id=task_id)
    previous_level = logger.level
    previous_propagate = logger.propagate
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    try:
        with progress:
            yield
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)
        logger.propagate = previous_propagate
        handler.close()
