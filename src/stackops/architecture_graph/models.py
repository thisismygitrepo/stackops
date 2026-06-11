from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias, TypedDict

ModuleName: TypeAlias = str
NodeId: TypeAlias = str


@dataclass(frozen=True, slots=True)
class PythonModule:
    name: ModuleName
    path: Path


@dataclass(frozen=True, slots=True)
class InternalImport:
    importer: ModuleName
    imported: ModuleName
    path: Path
    line: int


class NodePayload(TypedDict):
    id: str
    label: str
    group: str
    moduleCount: int
    fileCount: int


class EdgePayload(TypedDict):
    source: str
    target: str
    count: int


class GraphPayload(TypedDict):
    packageName: str
    sourceRoot: str
    depth: int
    generatedAt: str
    moduleCount: int
    importCount: int
    nodes: list[NodePayload]
    edges: list[EdgePayload]


class GraphPagePayload(TypedDict):
    packageName: str
    sourceRoot: str
    generatedAt: str
    initialDepth: int
    maxDepth: int
    depths: dict[str, GraphPayload]
