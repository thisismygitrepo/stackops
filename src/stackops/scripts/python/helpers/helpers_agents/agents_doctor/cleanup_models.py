import os
import stat
from dataclasses import dataclass, field
from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.models import HookEntry


@dataclass(frozen=True)
class CleanupRemoval:
    path: Path
    reviewed_stat: os.stat_result = field(init=False, repr=False)

    def __post_init__(self) -> None:
        reviewed = self.path.lstat()
        if stat.S_IFMT(reviewed.st_mode) not in (stat.S_IFREG, stat.S_IFDIR, stat.S_IFLNK):
            raise ValueError(f"Only regular files, directories, and symlinks can be removed: {self.path}")
        object.__setattr__(self, "reviewed_stat", reviewed)

    def verify_identity(self, *, path: Path) -> None:
        current = path.lstat()
        if not os.path.samestat(self.reviewed_stat, current) or stat.S_IFMT(self.reviewed_stat.st_mode) != stat.S_IFMT(current.st_mode):
            raise ValueError(f"Removal target changed since inspection; run agents reset again: {self.path}")


@dataclass(frozen=True)
class CleanupEdit:
    path: Path
    original: bytes
    mode: int
    replacement: bytes


type CleanupChange = CleanupRemoval | CleanupEdit


@dataclass(frozen=True)
class CleanupPlan:
    entries: tuple[HookEntry, ...]
    changes: tuple[CleanupChange, ...]
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class CleanupResult:
    changed_paths: tuple[Path, ...]
