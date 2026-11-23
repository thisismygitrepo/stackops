from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Literal, TypeAlias


Risk: TypeAlias = Literal["safe", "caution", "danger"]
type Platform = Literal["linux", "darwin", "windows"]
type Anchor = Literal[
    "home",
    "xdg_cache",
    "xdg_data",
    "xdg_config",
    "mac_caches",
    "local_app_data",
    "temp",
    "system_root",
    "cargo_home",
    "gradle_home",
    "hf_home",
    "filesystem_root",
]
type EstimateKind = Literal["exact", "at_least", "at_most", "approximate"]
type ActionKind = Literal["paths", "command", "projects"]
type TargetStatus = Literal["ready", "empty", "missing_tool", "failed"]
type OutcomeStatus = Literal["cleaned", "partial", "failed", "skipped"]
type DockerKind = Literal["Containers", "Images", "Local Volumes", "Build Cache"]


class CleanCategory(StrEnum):
    DEV = "dev"
    CONTAINERS = "containers"
    SYSTEM = "system"
    TRASH = "trash"
    PROJECTS = "projects"
    STACKOPS = "stackops"


@dataclass(frozen=True, slots=True)
class PathGlob:
    anchor: Anchor
    pattern: str


@dataclass(frozen=True, slots=True)
class PathCleanup:
    globs: tuple[PathGlob, ...]
    excluded_globs: tuple[PathGlob, ...]
    min_age_days: int | None
    requires_root: bool


@dataclass(frozen=True, slots=True)
class DetailItem:
    name: str
    note: str
    bytes: int | None


@dataclass(frozen=True, slots=True)
class TargetDetails:
    title: str
    count: int
    items: tuple[DetailItem, ...]


@dataclass(frozen=True, slots=True)
class CommandPlan:
    commands: tuple[tuple[str, ...], ...]
    measured_paths: tuple[Path, ...]
    reported_bytes: int | None
    estimate_kind: EstimateKind
    details: TargetDetails | None


@dataclass(frozen=True, slots=True)
class PlanFailure:
    message: str


@dataclass(frozen=True, slots=True)
class CommandCleanup:
    tool: str
    install_hint: str | None
    plan: Callable[[], CommandPlan | PlanFailure]
    requires_root: bool


@dataclass(frozen=True, slots=True)
class ProjectMarker:
    relation: Literal["sibling", "child"]
    name: str


@dataclass(frozen=True, slots=True)
class ProjectCleanup:
    directory_names: tuple[str, ...]
    marker: ProjectMarker | None


type CleanupAction = PathCleanup | CommandCleanup | ProjectCleanup


@dataclass(frozen=True, slots=True)
class ToolWithPathFallback:
    tool: CommandCleanup
    fallback: PathCleanup


type CatalogAction = CleanupAction | ToolWithPathFallback


@dataclass(frozen=True, slots=True)
class CleanTarget:
    key: str
    title: str
    category: CleanCategory
    risk: Risk
    note: str
    actions: Mapping[Platform, CatalogAction]


@dataclass(frozen=True, slots=True)
class Estimate:
    bytes: int | None
    kind: EstimateKind


@dataclass(frozen=True, slots=True)
class MeasuredPath:
    path: Path
    bytes: int


@dataclass(slots=True)
class SharedInode:
    links: int
    size: int
    seen: int


@dataclass(slots=True)
class Usage:
    exclusive: int
    shared: dict[tuple[int, int], SharedInode]
    newest_mtime: float
    denied: bool


@dataclass(frozen=True, slots=True)
class TargetScan:
    target: CleanTarget
    action: CleanupAction
    status: TargetStatus
    message: str
    paths: tuple[MeasuredPath, ...]
    commands: tuple[tuple[str, ...], ...]
    usage: Usage | None
    reported_bytes: int | None
    estimate: Estimate
    details: TargetDetails | None


@dataclass(frozen=True, slots=True)
class CleanOutcome:
    key: str
    status: OutcomeStatus
    freed_bytes: int | None
    message: str
