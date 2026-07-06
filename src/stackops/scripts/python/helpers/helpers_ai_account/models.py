from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from stackops.utils.schemas.fire_agents.fire_agents_types import AGENTS


type CredentialIdentity = tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RuntimeContext:
    home: Path
    environment: Mapping[str, str]
    system: str


type ActiveCredentialResolver = Callable[[RuntimeContext], Path]
type IdentityReader = Callable[[Path], CredentialIdentity | None]


@dataclass(frozen=True, slots=True)
class FileAgentSupport:
    agent: AGENTS
    display_name: str
    aliases: tuple[str, ...]
    backup_directory_name: str
    profile_file_name: Path
    resolve_active_credential: ActiveCredentialResolver
    read_identity: IdentityReader | None
    warning: str | None


@dataclass(frozen=True, slots=True)
class ManagedLoginAgentSupport:
    agent: AGENTS
    display_name: str
    aliases: tuple[str, ...]
    reason: str
    guidance: str


type AgentSupport = FileAgentSupport | ManagedLoginAgentSupport


class AutoRefreshUnavailableError(ValueError):
    pass


class CredentialStorageUnavailableError(ValueError):
    pass
