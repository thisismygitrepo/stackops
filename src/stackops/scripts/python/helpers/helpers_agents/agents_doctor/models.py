from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol, TypeAlias

from stackops.utils.schemas.fire_agents.fire_agents_types import AGENTS


type DoctorOrigin = Literal["local", "global", "admin", "system"]
type DoctorResourceKind = Literal["configuration", "plugin", "skill", "instructions"]
DoctorResourceFocus: TypeAlias = Literal["all", "configuration", "mcp", "plugin", "skill", "instructions"]
type DoctorResourceState = Literal["active", "available", "configured", "disabled", "missing", "shadowed"]
type DoctorSupportLevel = Literal["focused", "standard"]
type DoctorAgent = AGENTS | Literal["omp"]


@dataclass(frozen=True)
class DoctorContext:
    working_directory: Path
    project_root: Path
    ancestor_directories: tuple[Path, ...]
    home_directory: Path
    xdg_config_directory: Path
    xdg_data_directory: Path
    codex_home: Path
    pi_home: Path
    omp_home: Path
    claude_home: Path


@dataclass(frozen=True)
class DoctorResource:
    kind: DoctorResourceKind
    is_mcp: bool
    name: str
    origin: DoctorOrigin
    state: DoctorResourceState
    path: Path
    detail: str


class DoctorCollector(Protocol):
    def __call__(self, *, context: DoctorContext) -> tuple[DoctorResource, ...]: ...


@dataclass(frozen=True)
class DoctorAgentDefinition:
    agent: DoctorAgent
    display_name: str
    executable: str
    version_arguments: tuple[str, ...]
    support_level: DoctorSupportLevel
    collector: DoctorCollector
    notes: tuple[str, ...]


@dataclass(frozen=True)
class DoctorExecutableStatus:
    installed: bool
    path: Path | None
    version: str | None
    error: str | None


@dataclass(frozen=True)
class DoctorReport:
    definition: DoctorAgentDefinition
    context: DoctorContext
    executable: DoctorExecutableStatus
    resources: tuple[DoctorResource, ...]
