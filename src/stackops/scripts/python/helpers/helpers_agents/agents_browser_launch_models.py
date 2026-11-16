from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeAlias

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import BrowserMultiplexer, BrowserName, BrowserRuntime


@dataclass(frozen=True)
class BrowserLaunchDetails:
    browser: BrowserName
    browser_path: Path
    command: tuple[str, ...]
    endpoint_label: str
    endpoint_short_label: str
    process_label: str
    host: str
    port: int
    browser_port: int
    profile_path: Path | None


@dataclass(frozen=True)
class BrowserWindowHandle:
    multiplexer: BrowserMultiplexer
    session_name: str
    targets: tuple[str, ...]
    attach_script: str


@dataclass(frozen=True)
class NewBrowserLaunchResult(BrowserLaunchDetails):
    process_id: int
    relay_process_id: int | None
    windows: BrowserWindowHandle | None


BrowserLaunchOwner: TypeAlias = BrowserRuntime | Literal["external"]


@dataclass(frozen=True)
class ExistingBrowserLaunchResult(BrowserLaunchDetails):
    process_id: int
    owner: BrowserLaunchOwner
    opened_page: bool
    repaired_relay: bool


BrowserLaunchResult: TypeAlias = NewBrowserLaunchResult | ExistingBrowserLaunchResult


def build_new_launch_result(
    *, details: BrowserLaunchDetails, process_id: int, relay_process_id: int | None, windows: BrowserWindowHandle | None
) -> NewBrowserLaunchResult:
    return NewBrowserLaunchResult(
        browser=details.browser,
        browser_path=details.browser_path,
        command=details.command,
        endpoint_label=details.endpoint_label,
        endpoint_short_label=details.endpoint_short_label,
        process_label=details.process_label,
        host=details.host,
        port=details.port,
        browser_port=details.browser_port,
        profile_path=details.profile_path,
        process_id=process_id,
        relay_process_id=relay_process_id,
        windows=windows,
    )


def build_existing_launch_result(
    *,
    details: BrowserLaunchDetails,
    process_id: int,
    owner: BrowserLaunchOwner,
    opened_page: bool,
    repaired_relay: bool,
) -> ExistingBrowserLaunchResult:
    return ExistingBrowserLaunchResult(
        browser=details.browser,
        browser_path=details.browser_path,
        command=details.command,
        endpoint_label=details.endpoint_label,
        endpoint_short_label=details.endpoint_short_label,
        process_label=details.process_label,
        host=details.host,
        port=details.port,
        browser_port=details.browser_port,
        profile_path=details.profile_path,
        process_id=process_id,
        owner=owner,
        opened_page=opened_page,
        repaired_relay=repaired_relay,
    )
