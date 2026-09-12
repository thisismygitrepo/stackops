from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeAlias

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.models import HookEntry


CleanupScope: TypeAlias = Literal["local", "global", "all"]


@dataclass(frozen=True)
class CleanupFile:
    relative_path: Path
    content: bytes
    mode: int


@dataclass(frozen=True)
class CleanupSnapshot:
    path: Path
    directory: bool
    files: tuple[CleanupFile, ...]
    directories: tuple[tuple[Path, int], ...]
    links: tuple[tuple[Path, str], ...]


@dataclass(frozen=True)
class CleanupChange:
    snapshot: CleanupSnapshot
    replacement: bytes | None


@dataclass(frozen=True)
class CleanupPlan:
    entries: tuple[HookEntry, ...]
    changes: tuple[CleanupChange, ...]
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class CleanupResult:
    changed_paths: tuple[Path, ...]
    backup_directory: Path | None
