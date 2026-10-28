from dataclasses import dataclass
from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.models import HookEntry


@dataclass(frozen=True)
class CleanupRemoval:
    path: Path


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
