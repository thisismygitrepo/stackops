from enum import StrEnum
from typing import Literal, TypedDict


class RemoteBranchSnapshot(TypedDict):
    name: str
    commit: str


class RemoteSnapshot(TypedDict):
    name: str
    urls: list[str]
    branches: list[RemoteBranchSnapshot]


class RepositorySnapshot(TypedDict):
    path: str
    branch: str | None
    commit: str
    isDirty: bool
    remotes: list[RemoteSnapshot]


class DeclaredVersion(TypedDict):
    version: str
    message: str
    repositories: list[RepositorySnapshot]


class VersionsFile(TypedDict):
    schemaVersion: Literal["1"]
    versions: list[DeclaredVersion]


class VersionRepositoryState(StrEnum):
    exact = "exact"
    different = "different"
    dirty = "dirty"
    missing = "missing"
    unverifiable = "unverifiable"


class RepositoryVersionStatus(TypedDict):
    snapshot: RepositorySnapshot
    state: VersionRepositoryState
    detail: str


class RepositoryCheckoutResult(TypedDict):
    path: str
    branch: str | None
    commit: str
    changed: bool
    needsFetch: bool
    backupRefs: list[str]
