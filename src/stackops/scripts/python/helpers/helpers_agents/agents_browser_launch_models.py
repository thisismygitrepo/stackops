from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import BrowserName
from stackops.scripts.python.helpers.helpers_agents.agents_browser_tmux_models import BrowserTmuxLaunch


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
    prompt_path: Path


@dataclass(frozen=True)
class DetachedBrowserLaunchResult(BrowserLaunchDetails):
    process_id: int
    relay_process_id: int | None


@dataclass(frozen=True)
class TmuxBrowserLaunchResult(BrowserLaunchDetails):
    tmux: BrowserTmuxLaunch


BrowserLaunchResult: TypeAlias = DetachedBrowserLaunchResult | TmuxBrowserLaunchResult


def build_detached_launch_result(*, details: BrowserLaunchDetails, process_id: int, relay_process_id: int | None) -> DetachedBrowserLaunchResult:
    return DetachedBrowserLaunchResult(
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
        prompt_path=details.prompt_path,
        process_id=process_id,
        relay_process_id=relay_process_id,
    )


def build_tmux_launch_result(*, details: BrowserLaunchDetails, tmux: BrowserTmuxLaunch) -> TmuxBrowserLaunchResult:
    return TmuxBrowserLaunchResult(
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
        prompt_path=details.prompt_path,
        tmux=tmux,
    )
