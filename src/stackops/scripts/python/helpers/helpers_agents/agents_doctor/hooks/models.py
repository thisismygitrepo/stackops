from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorAgent, DoctorOrigin, DoctorResourceState


type HookFormat = Literal["json", "toml", "file", "directory", "yaml"]
type HookSelector = tuple[str | int, ...]


@dataclass(frozen=True)
class HookRemoval:
    path: Path
    format: HookFormat
    selector: HookSelector
    action: Literal["delete", "disable"]


@dataclass(frozen=True)
class HookEntry:
    agent: DoctorAgent
    origin: DoctorOrigin
    path: Path
    name: str
    event: str
    command: str
    state: DoctorResourceState
    removal: HookRemoval | None


@dataclass(frozen=True)
class HookDiagnostic:
    agent: DoctorAgent
    origin: DoctorOrigin
    path: Path
    message: str
    severity: Literal["error", "notice"]


@dataclass(frozen=True)
class HookInventory:
    entries: tuple[HookEntry, ...]
    diagnostics: tuple[HookDiagnostic, ...]


@dataclass(frozen=True)
class HookSource:
    agent: DoctorAgent
    origin: DoctorOrigin
    path: Path
    selector: HookSelector
