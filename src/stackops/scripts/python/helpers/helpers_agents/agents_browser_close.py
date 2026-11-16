from dataclasses import dataclass
import os
from pathlib import Path
from typing import TypeAlias

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import (
    BROWSER_PROFILES_ROOT,
    TEMPORARY_BROWSER_PROFILE_DIRECTORY_NAME,
    BrowserName,
    BrowserRuntime,
    ProfileBrowserName,
)
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_lock import browser_launch_lock
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_records import (
    BrowserLaunchRecord,
    list_browser_launch_record_paths,
    read_browser_launch_record,
)
from stackops.scripts.python.helpers.helpers_agents.agents_browser_lifecycle import retire_browser_launch


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
class ClosedBrowserLaunch:
    launch_id: str
    runtime: BrowserRuntime


@dataclass(frozen=True, slots=True)
class BrowserLaunchCloseResult:
    scope: BrowserCloseScope
    closed: tuple[ClosedBrowserLaunch, ...]


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


def describe_closed_runtimes(*, result: BrowserLaunchCloseResult) -> str:
    runtimes = [launch.runtime for launch in result.closed]
    return ", ".join(f"{runtimes.count(runtime)} {runtime}" for runtime in sorted(set(runtimes)))


def _close_tracked_browser_launches(*, scope: BrowserCloseScope) -> BrowserLaunchCloseResult:
    closed: list[ClosedBrowserLaunch] = []
    errors: list[str] = []
    with browser_launch_lock():
        try:
            record_paths = list_browser_launch_record_paths()
        except RuntimeError as error:
            errors.append(str(error))
            record_paths = ()
        for record_path in record_paths:
            try:
                launch = read_browser_launch_record(record_path=record_path)
                if not _launch_in_scope(launch=launch, scope=scope):
                    continue
                retire_browser_launch(launch=launch, record_path=record_path)
            except (OSError, RuntimeError) as error:
                errors.append(f"{record_path}: {error}")
                continue
            closed.append(ClosedBrowserLaunch(launch_id=launch.launch_id, runtime="detached" if launch.windows is None else launch.windows.multiplexer))
    if errors:
        details = "\n".join(f"- {error}" for error in errors)
        raise RuntimeError(f"{_close_failure_headline(scope=scope)}\n{details}")
    return BrowserLaunchCloseResult(scope=scope, closed=tuple(closed))


def _close_failure_headline(*, scope: BrowserCloseScope) -> str:
    match scope:
        case SingleBrowserLaunch(browser=browser, port=port):
            return f"Could not close the {browser} launch on port {port}:"
        case SavedProfileBrowserLaunches(browser=browser):
            return f"Could not close every {browser} saved-profile launch:"
        case NamedProfileBrowserLaunches(browser=browser, profile_names=profile_names):
            return f"Could not close every requested {browser} profile launch ({', '.join(profile_names)}):"


def _launch_in_scope(*, launch: BrowserLaunchRecord, scope: BrowserCloseScope) -> bool:
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
