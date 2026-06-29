from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeAlias

DependencyBackend: TypeAlias = Literal["pyan", "pydeps"]
DependencyOutput: TypeAlias = Literal["json", "jsonic", "html"]
DependencyRankDirection: TypeAlias = Literal["TB", "BT", "LR", "RL"]
DependencyEdgeFilter: TypeAlias = Literal["all", "cycles", "dual"]
type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]


@dataclass(frozen=True, order=True)
class DependencyNode:
    name: str
    path: str | None


@dataclass(frozen=True, order=True)
class DependencyEdge:
    importer: str
    imported: str


@dataclass(frozen=True, order=True)
class DualDependency:
    left: str
    right: str


@dataclass(frozen=True)
class DependencyGraph:
    nodes: tuple[DependencyNode, ...]
    edges: tuple[DependencyEdge, ...]


@dataclass(frozen=True)
class DependencyCheckContext:
    repo_root: Path
    target_path: Path


@dataclass(frozen=True)
class DependencyReport:
    backend: DependencyBackend
    repo_root: Path
    target_path: Path
    edge_filter: DependencyEdgeFilter
    nodes: tuple[DependencyNode, ...]
    edges: tuple[DependencyEdge, ...]
    dual_dependencies: tuple[DualDependency, ...]
    cycle_groups: tuple[tuple[str, ...], ...]
