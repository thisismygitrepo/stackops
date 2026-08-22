from dataclasses import dataclass
import os
from pathlib import Path
import shutil
from typing import TypeAlias

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import (
    BROWSER_DETACHED_LAUNCHES_ROOT,
    BROWSER_PROFILES_ROOT,
    TEMPORARY_BROWSER_PROFILE_DIRECTORY_NAME,
    BrowserName,
    ProfileBrowserName,
)
from stackops.scripts.python.helpers.helpers_agents.agents_browser_detached_processes import (
    terminate_browser_launch_process,
    terminate_registered_process,
)
from stackops.scripts.python.helpers.helpers_agents.agents_browser_detached_status import DetachedBrowserLaunchRecord, read_detached_browser_launch
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_lock import browser_launch_lock
from stackops.scripts.python.helpers.helpers_agents.agents_browser_tmux import close_browser_tmux_windows, collect_browser_tmux_status
from stackops.scripts.python.helpers.helpers_agents.agents_browser_tmux_models import BrowserTmuxPaneStatus


@dataclass(frozen=True, slots=True)
class SingleBrowserLaunch:
    browser: BrowserName
    port: int


@dataclass(frozen=True, slots=True)
class SavedProfileBrowserLaunches:
    browser: ProfileBrowserName


@dataclass(frozen=True, slots=True)
class NamedProfileBrowserLaunches:
    browser: ProfileBrowserName
    profile_names: tuple[str, ...]


BrowserCloseScope: TypeAlias = SingleBrowserLaunch | SavedProfileBrowserLaunches | NamedProfileBrowserLaunches


@dataclass(frozen=True, slots=True)
class BrowserLaunchCloseResult:
    scope: BrowserCloseScope
    tmux_launch_ids: tuple[str, ...]
    detached_launch_ids: tuple[str, ...]

    @property
    def closed_count(self) -> int:
        return len(self.tmux_launch_ids) + len(self.detached_launch_ids)


def close_browser_launch(*, browser: BrowserName, port: int) -> BrowserLaunchCloseResult:
    """Close the StackOps-tracked launch for one browser endpoint port."""
    return _close_tracked_browser_launches(scope=SingleBrowserLaunch(browser=browser, port=port))


def close_all_browser_profile_launches(*, browser: ProfileBrowserName) -> BrowserLaunchCloseResult:
    """Close every StackOps-tracked saved-profile launch for one browser."""
    return _close_tracked_browser_launches(scope=SavedProfileBrowserLaunches(browser=browser))


def close_named_browser_profile_launches(*, browser: ProfileBrowserName, profile_names: tuple[str, ...]) -> BrowserLaunchCloseResult:
    """Close the StackOps-tracked launches for selected saved profiles of one browser."""
    if not profile_names:
        raise ValueError("profile_names must not be empty")
    return _close_tracked_browser_launches(scope=NamedProfileBrowserLaunches(browser=browser, profile_names=profile_names))


def _close_tracked_browser_launches(*, scope: BrowserCloseScope) -> BrowserLaunchCloseResult:
    errors: list[str] = []
    tmux_launch_ids: tuple[str, ...] = ()
    detached_launch_ids: tuple[str, ...] = ()
    with browser_launch_lock():
        try:
            tmux_launch_ids = _close_tmux_browser_launches(scope=scope)
        except RuntimeError as error:
            errors.append(str(error))
        try:
            detached_launch_ids = _close_detached_browser_launches(scope=scope)
        except RuntimeError as error:
            errors.append(str(error))
    if errors:
        details = "\n".join(f"- {error}" for error in errors)
        raise RuntimeError(f"{_close_failure_headline(scope=scope)}\n{details}")
    return BrowserLaunchCloseResult(scope=scope, tmux_launch_ids=tmux_launch_ids, detached_launch_ids=detached_launch_ids)


def _close_failure_headline(*, scope: BrowserCloseScope) -> str:
    match scope:
        case SingleBrowserLaunch(browser=browser, port=port):
            return f"Could not close the {browser} launch on port {port}:"
        case SavedProfileBrowserLaunches(browser=browser):
            return f"Could not close every {browser} saved-profile launch:"
        case NamedProfileBrowserLaunches(browser=browser, profile_names=profile_names):
            return f"Could not close every requested {browser} profile launch ({', '.join(profile_names)}):"


def _close_tmux_browser_launches(*, scope: BrowserCloseScope) -> tuple[str, ...]:
    if shutil.which("tmux") is None:
        return ()
    rows = collect_browser_tmux_status()
    launch_ids = tuple(
        sorted({row.metadata.launch_id for row in rows if row.metadata.role == "endpoint" and _tmux_endpoint_in_scope(row=row, scope=scope)})
    )
    matching_launch_ids = set(launch_ids)
    window_ids = tuple(sorted({row.window_id for row in rows if row.metadata.launch_id in matching_launch_ids}))
    close_browser_tmux_windows(window_ids=window_ids)
    return launch_ids


def _close_detached_browser_launches(*, scope: BrowserCloseScope) -> tuple[str, ...]:
    if not BROWSER_DETACHED_LAUNCHES_ROOT.exists():
        return ()
    try:
        record_paths = tuple(sorted(BROWSER_DETACHED_LAUNCHES_ROOT.glob("*.json")))
    except OSError as error:
        raise RuntimeError(f"Could not read detached browser launch records under {BROWSER_DETACHED_LAUNCHES_ROOT}: {error}") from error

    launch_ids: list[str] = []
    errors: list[str] = []
    for record_path in record_paths:
        try:
            launch = read_detached_browser_launch(record_path=record_path)
            if not _detached_launch_in_scope(launch=launch, scope=scope):
                continue
            _terminate_detached_launch(launch=launch)
            record_path.unlink()
        except (OSError, RuntimeError) as error:
            errors.append(f"{record_path}: {error}")
            continue
        launch_ids.append(launch.launch_id)
    if errors:
        details = "\n".join(f"  - {error}" for error in errors)
        raise RuntimeError(f"Detached launch close failures:\n{details}")
    return tuple(launch_ids)


def _tmux_endpoint_in_scope(*, row: BrowserTmuxPaneStatus, scope: BrowserCloseScope) -> bool:
    match scope:
        case SingleBrowserLaunch(browser=browser, port=port):
            return row.metadata.browser == browser and row.metadata.port == str(port)
        case SavedProfileBrowserLaunches(browser=browser):
            return row.metadata.browser == browser and _saved_profile_name(profile_path=Path(row.metadata.profile_path), browser=browser) is not None
        case NamedProfileBrowserLaunches(browser=browser, profile_names=profile_names):
            if row.metadata.browser != browser:
                return False
            profile_name = _saved_profile_name(profile_path=Path(row.metadata.profile_path), browser=browser)
            return profile_name is not None and profile_name in profile_names


def _detached_launch_in_scope(*, launch: DetachedBrowserLaunchRecord, scope: BrowserCloseScope) -> bool:
    match scope:
        case SingleBrowserLaunch(browser=browser, port=port):
            return launch.browser == browser and launch.port == port
        case SavedProfileBrowserLaunches(browser=browser):
            if launch.browser != browser or launch.profile_path is None:
                return False
            return _saved_profile_name(profile_path=launch.profile_path, browser=browser) is not None
        case NamedProfileBrowserLaunches(browser=browser, profile_names=profile_names):
            if launch.browser != browser or launch.profile_path is None:
                return False
            profile_name = _saved_profile_name(profile_path=launch.profile_path, browser=browser)
            return profile_name is not None and profile_name in profile_names


def _terminate_detached_launch(*, launch: DetachedBrowserLaunchRecord) -> None:
    relay_identity_is_incomplete = (launch.relay_process_id is None) != (launch.relay_process_created_at is None)
    if relay_identity_is_incomplete:
        raise RuntimeError("relay process identity is incomplete")
    if launch.relay_process_id is not None and launch.relay_process_created_at is not None:
        terminate_registered_process(
            process_id=launch.relay_process_id, process_created_at=launch.relay_process_created_at, process_label="browser endpoint LAN relay"
        )
    terminate_browser_launch_process(
        browser=launch.browser,
        browser_port=launch.browser_port,
        profile_path=launch.profile_path,
        process_id=launch.process_id,
        process_created_at=launch.process_created_at,
        process_label=f"{launch.browser} browser",
    )


def _saved_profile_name(*, profile_path: Path, browser: ProfileBrowserName) -> str | None:
    browser_profiles_root = BROWSER_PROFILES_ROOT.expanduser().joinpath(browser)
    browser_profiles_root_key = _lexical_path_key(path=browser_profiles_root)
    if _lexical_path_key(path=profile_path.parent) == browser_profiles_root_key:
        return profile_path.name
    if (
        profile_path.parent.name == TEMPORARY_BROWSER_PROFILE_DIRECTORY_NAME
        and _lexical_path_key(path=profile_path.parents[1].parent) == browser_profiles_root_key
    ):
        return profile_path.parents[1].name
    return None


def _lexical_path_key(*, path: Path) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(path.expanduser())))
