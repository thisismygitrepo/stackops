from dataclasses import dataclass
import os
from pathlib import Path
import re
import shutil

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import (
    BROWSER_DETACHED_LAUNCHES_ROOT,
    BROWSER_PROFILES_ROOT,
    DEFAULT_BROWSER_PROFILE_PORT_START,
    TEMPORARY_BROWSER_PROFILE_DIRECTORY_NAME,
    ProfileBrowserName,
)
from stackops.scripts.python.helpers.helpers_agents.agents_browser_detached_processes import (
    terminate_browser_launch_process,
    terminate_registered_process,
)
from stackops.scripts.python.helpers.helpers_agents.agents_browser_detached_status import read_detached_browser_launch
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_lock import browser_launch_lock
from stackops.scripts.python.helpers.helpers_agents.agents_browser_profile_listing import list_browser_profile_paths, natural_profile_name_key
from stackops.scripts.python.helpers.helpers_agents.agents_browser_tmux import close_browser_tmux_windows, collect_browser_tmux_status


@dataclass(frozen=True, slots=True)
class BrowserProfileLaunchSpec:
    browser: ProfileBrowserName
    profile_name: str
    profile_path: Path
    port: int


@dataclass(frozen=True, slots=True)
class BrowserProfileCloseResult:
    browser: ProfileBrowserName
    tmux_launch_ids: tuple[str, ...]
    detached_launch_ids: tuple[str, ...]

    @property
    def closed_count(self) -> int:
        return len(self.tmux_launch_ids) + len(self.detached_launch_ids)


def build_browser_profile_launch_specs(
    *, browser: ProfileBrowserName, port_start: int = DEFAULT_BROWSER_PROFILE_PORT_START
) -> tuple[BrowserProfileLaunchSpec, ...]:
    _validate_port_start(port_start=port_start)
    profile_paths = list_browser_profile_paths(browser=browser)

    port_by_profile = _assign_profile_ports(profile_paths=profile_paths, port_start=port_start)
    specs = tuple(
        BrowserProfileLaunchSpec(browser=browser, profile_name=profile_path.name, profile_path=profile_path, port=port_by_profile[profile_path.name])
        for profile_path in profile_paths
    )
    return tuple(sorted(specs, key=lambda spec: (spec.port, natural_profile_name_key(name=spec.profile_name))))


def close_browser_profile_launches(*, browser: ProfileBrowserName) -> BrowserProfileCloseResult:
    """Close StackOps-tracked launches for saved profiles of one browser."""
    errors: list[str] = []
    tmux_launch_ids: tuple[str, ...] = ()
    detached_launch_ids: tuple[str, ...] = ()
    with browser_launch_lock():
        try:
            tmux_launch_ids = _close_tmux_browser_profile_launches(browser=browser)
        except RuntimeError as error:
            errors.append(str(error))
        try:
            detached_launch_ids = _close_detached_browser_profile_launches(browser=browser)
        except RuntimeError as error:
            errors.append(str(error))
    if errors:
        details = "\n".join(f"- {error}" for error in errors)
        raise RuntimeError(f"Could not close every {browser} saved-profile launch:\n{details}")
    return BrowserProfileCloseResult(browser=browser, tmux_launch_ids=tmux_launch_ids, detached_launch_ids=detached_launch_ids)


def _close_tmux_browser_profile_launches(*, browser: ProfileBrowserName) -> tuple[str, ...]:
    if shutil.which("tmux") is None:
        return ()
    rows = collect_browser_tmux_status()
    launch_ids = tuple(
        sorted(
            {
                row.metadata.launch_id
                for row in rows
                if row.metadata.role == "endpoint"
                and row.metadata.browser == browser
                and _is_saved_browser_profile(profile_path=Path(row.metadata.profile_path), browser=browser)
            }
        )
    )
    matching_launch_ids = set(launch_ids)
    window_ids = tuple(sorted({row.window_id for row in rows if row.metadata.launch_id in matching_launch_ids}))
    close_browser_tmux_windows(window_ids=window_ids)
    return launch_ids


def _close_detached_browser_profile_launches(*, browser: ProfileBrowserName) -> tuple[str, ...]:
    if not BROWSER_DETACHED_LAUNCHES_ROOT.exists():
        return ()
    try:
        record_paths = tuple(sorted(BROWSER_DETACHED_LAUNCHES_ROOT.glob("*.json")))
    except OSError as error:
        raise RuntimeError(f"Could not read detached browser launch records under {BROWSER_DETACHED_LAUNCHES_ROOT}: {error}") from error

    launch_ids: list[str] = []
    errors: list[str] = []
    for record_path in record_paths:
        if not record_path.stem.startswith(f"{browser}-"):
            continue
        try:
            launch = read_detached_browser_launch(record_path=record_path)
            if launch.browser != browser or launch.profile_path is None:
                continue
            if not _is_saved_browser_profile(profile_path=launch.profile_path, browser=browser):
                continue
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
                process_label=f"{browser} browser",
            )
            record_path.unlink()
        except (OSError, RuntimeError) as error:
            errors.append(f"{record_path}: {error}")
            continue
        launch_ids.append(launch.launch_id)
    if errors:
        details = "\n".join(f"  - {error}" for error in errors)
        raise RuntimeError(f"Detached launch close failures:\n{details}")
    return tuple(launch_ids)


def _is_saved_browser_profile(*, profile_path: Path, browser: ProfileBrowserName) -> bool:
    browser_profiles_root = BROWSER_PROFILES_ROOT.expanduser().joinpath(browser)
    browser_profiles_root_key = _lexical_path_key(path=browser_profiles_root)
    if _lexical_path_key(path=profile_path.parent) == browser_profiles_root_key:
        return True
    return (
        profile_path.parent.name == TEMPORARY_BROWSER_PROFILE_DIRECTORY_NAME
        and _lexical_path_key(path=profile_path.parents[1].parent) == browser_profiles_root_key
    )


def _lexical_path_key(*, path: Path) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(path.expanduser())))


def _assign_profile_ports(*, profile_paths: tuple[Path, ...], port_start: int) -> dict[str, int]:
    maximum_port = 65535
    port_by_profile: dict[str, int] = {}
    reserved_ports: dict[int, str] = {}
    unnumbered_profile_names: list[str] = []

    for profile_path in profile_paths:
        profile_number = _profile_number(profile_name=profile_path.name)
        if profile_number is None:
            unnumbered_profile_names.append(profile_path.name)
            continue
        port = port_start + profile_number
        if port > maximum_port:
            raise ValueError(f"Profile {profile_path.name} maps to port {port}, which is outside the valid port range")
        conflicting_profile = reserved_ports.get(port)
        if conflicting_profile is not None:
            raise ValueError(f"Profiles {conflicting_profile} and {profile_path.name} both map to port {port}")
        reserved_ports[port] = profile_path.name
        port_by_profile[profile_path.name] = port

    next_port = port_start + 1
    for profile_name in unnumbered_profile_names:
        while next_port in reserved_ports and next_port <= maximum_port:
            next_port += 1
        if next_port > maximum_port:
            raise ValueError(f"There are too many browser profiles to assign ports after {port_start}")
        port_by_profile[profile_name] = next_port
        reserved_ports[next_port] = profile_name
        next_port += 1
    return port_by_profile


def _profile_number(*, profile_name: str) -> int | None:
    match = re.fullmatch(r"p([1-9]\d*)", profile_name, flags=re.IGNORECASE)
    if match is None:
        return None
    profile_number = int(match.group(1))
    if str(profile_number) != match.group(1):
        return None
    return profile_number


def _validate_port_start(*, port_start: int) -> None:
    if port_start < 1 or port_start > 65534:
        raise ValueError("--port-start must be between 1 and 65534")
