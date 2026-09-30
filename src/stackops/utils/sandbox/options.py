from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class SandboxBackend(StrEnum):
    NONE = "none"
    DOCKER = "docker"
    PODMAN = "podman"
    BWRAP = "bwrap"
    SRT = "srt"
    AI_JAIL = "ai-jail"
    OPENSHELL = "openshell"


class SandboxSync(StrEnum):
    COPY_BACK = "copy-back"
    MANUAL = "manual"


@dataclass(frozen=True, slots=True)
class SandboxOptions:
    backend: SandboxBackend
    image: str | None
    settings: Path | None
    providers: tuple[str, ...]
    name: str | None
    sync: SandboxSync | None


@dataclass(frozen=True, slots=True)
class SandboxAccess:
    writable_paths: tuple[Path, ...]
    environment_names: tuple[str, ...]
    environment_overrides: dict[str, str]
