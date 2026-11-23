import os
import re
import stat
import sys
from collections.abc import Iterable
from pathlib import Path

from stackops.scripts.python.helpers.helpers_utils.clean_drive_models import SharedInode, Usage


SIZE_PATTERN = re.compile(r"^(?P<number>\d+(?:\.\d+)?)\s*(?P<prefix>[kKMGTP]?)(?P<binary>i?)(?P<suffix>B?)$")


def _record(usage: Usage, entry_stat: os.stat_result) -> None:
    if sys.platform == "win32":
        size = entry_stat.st_size
    else:
        size = entry_stat.st_blocks * 512
    usage.newest_mtime = max(usage.newest_mtime, entry_stat.st_mtime)
    if entry_stat.st_nlink > 1 and not stat.S_ISDIR(entry_stat.st_mode):
        inode = (entry_stat.st_dev, entry_stat.st_ino)
        shared = usage.shared.get(inode)
        if shared is None:
            usage.shared[inode] = SharedInode(links=entry_stat.st_nlink, size=size, seen=1)
        else:
            shared.seen += 1
        return
    usage.exclusive += size


def measure_path(path: Path) -> Usage:
    usage = Usage(exclusive=0, shared={}, newest_mtime=0.0, denied=False)
    try:
        top_stat = path.lstat()
    except FileNotFoundError:
        return usage
    except PermissionError:
        usage.denied = True
        return usage
    _record(usage, top_stat)
    if not stat.S_ISDIR(top_stat.st_mode):
        return usage
    pending = [os.fspath(path)]
    while pending:
        directory = pending.pop()
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    try:
                        entry_stat = entry.stat(follow_symlinks=False)
                    except FileNotFoundError:
                        continue
                    _record(usage, entry_stat)
                    if stat.S_ISDIR(entry_stat.st_mode):
                        pending.append(entry.path)
        except PermissionError:
            usage.denied = True
        except FileNotFoundError:
            continue
    return usage


def _absorb(combined: Usage, usage: Usage) -> None:
    combined.exclusive += usage.exclusive
    combined.newest_mtime = max(combined.newest_mtime, usage.newest_mtime)
    combined.denied = combined.denied or usage.denied
    for inode, shared in usage.shared.items():
        existing = combined.shared.get(inode)
        if existing is None:
            combined.shared[inode] = SharedInode(links=shared.links, size=shared.size, seen=shared.seen)
        else:
            existing.seen += shared.seen


def combine_usages(usages: Iterable[Usage]) -> Usage:
    combined = Usage(exclusive=0, shared={}, newest_mtime=0.0, denied=False)
    for usage in usages:
        _absorb(combined, usage)
    return combined


def measure_directory(path: Path) -> tuple[Usage, dict[str, int]]:
    usage = Usage(exclusive=0, shared={}, newest_mtime=0.0, denied=False)
    _record(usage, path.lstat())
    entry_bytes: dict[str, int] = {}
    try:
        with os.scandir(path) as entries:
            names = [entry.name for entry in entries]
    except PermissionError:
        usage.denied = True
        return usage, entry_bytes
    for name in names:
        entry_usage = measure_path(path / name)
        entry_bytes[name] = reclaimable_bytes(entry_usage)
        _absorb(usage, entry_usage)
    return usage, entry_bytes


def reclaimable_bytes(usage: Usage) -> int:
    return usage.exclusive + sum(shared.size for shared in usage.shared.values() if shared.seen >= shared.links)


def parse_size(text: str) -> int:
    match = SIZE_PATTERN.match(text.strip())
    if match is None:
        raise ValueError(f"""Unrecognised size {text!r}""")
    prefix = match["prefix"].upper()
    exponent = "KMGTP".index(prefix) + 1 if prefix else 0
    binary = match["binary"] == "i" or (prefix != "" and match["suffix"] == "")
    return round(float(match["number"]) * (1024 if binary else 1000) ** exponent)
