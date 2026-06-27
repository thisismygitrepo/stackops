from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol, TypeAlias

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import BrowserName

BrowserEndpointProtocol: TypeAlias = Literal["cdp", "webdriver-bidi", "webdriver"]
BrowserProfileMode: TypeAlias = Literal["stackops-profile", "unsupported"]


class BrowserKnownPathResolver(Protocol):
    def __call__(self, *, system_name: str) -> tuple[Path, ...]: ...


class BrowserCommandBuilder(Protocol):
    def __call__(self, *, browser_path: Path, port: int, profile_path: Path | None) -> tuple[str, ...]: ...


@dataclass(frozen=True)
class BrowserLauncher:
    browser: BrowserName
    display_name: str
    command_names: tuple[str, ...]
    known_paths: BrowserKnownPathResolver
    build_command: BrowserCommandBuilder
    endpoint_protocol: BrowserEndpointProtocol
    endpoint_label: str
    endpoint_short_label: str
    process_label: str
    profile_mode: BrowserProfileMode
    setup_note: str | None
