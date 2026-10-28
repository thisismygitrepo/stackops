import stat
from pathlib import Path

from rich.filesize import decimal

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_models import CleanupChange, CleanupEdit, CleanupRemoval


def measure_tree(*, path: Path) -> tuple[int, int]:
    seen: set[tuple[int, int]] = set()
    files = 0
    total_bytes = 0
    pending = [path]
    while pending:
        current = pending.pop()
        current_stat = current.lstat()
        if stat.S_ISDIR(current_stat.st_mode):
            pending.extend(current.iterdir())
        elif (current_stat.st_dev, current_stat.st_ino) not in seen:
            seen.add((current_stat.st_dev, current_stat.st_ino))
            files += 1
            total_bytes += current_stat.st_size
    return files, total_bytes


def describe_change_size(*, change: CleanupChange) -> str:
    match change:
        case CleanupEdit():
            return decimal(len(change.original))
        case CleanupRemoval():
            files, total_bytes = measure_tree(path=change.path)
            return f"""{decimal(total_bytes)} · {files:,} {"file" if files == 1 else "files"}"""
