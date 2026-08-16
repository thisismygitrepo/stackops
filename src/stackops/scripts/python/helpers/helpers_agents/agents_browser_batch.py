from dataclasses import dataclass
from pathlib import Path
import re

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import (
    BROWSER_PROFILES_ROOT,
    DEFAULT_BROWSER_PROFILE_PORT_START,
    ProfileBrowserName,
)


@dataclass(frozen=True, slots=True)
class BrowserProfileLaunchSpec:
    browser: ProfileBrowserName
    profile_name: str
    profile_path: Path
    port: int


def build_browser_profile_launch_specs(
    *, browser: ProfileBrowserName, port_start: int = DEFAULT_BROWSER_PROFILE_PORT_START
) -> tuple[BrowserProfileLaunchSpec, ...]:
    _validate_port_start(port_start=port_start)
    browser_profiles_root = BROWSER_PROFILES_ROOT.expanduser().joinpath(browser)
    if not browser_profiles_root.is_dir():
        raise RuntimeError(f"Browser profiles directory does not exist: {browser_profiles_root}")

    try:
        profile_paths = tuple(
            sorted((path for path in browser_profiles_root.iterdir() if path.is_dir()), key=lambda path: _natural_name_key(name=path.name))
        )
    except OSError as error:
        raise RuntimeError(f"Could not read browser profiles directory {browser_profiles_root}: {error}") from error
    if len(profile_paths) == 0:
        raise RuntimeError(f"No browser profiles found under: {browser_profiles_root}")

    port_by_profile = _assign_profile_ports(profile_paths=profile_paths, port_start=port_start)
    specs = tuple(
        BrowserProfileLaunchSpec(browser=browser, profile_name=profile_path.name, profile_path=profile_path, port=port_by_profile[profile_path.name])
        for profile_path in profile_paths
    )
    return tuple(sorted(specs, key=lambda spec: (spec.port, _natural_name_key(name=spec.profile_name))))


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


def _natural_name_key(*, name: str) -> tuple[tuple[int, int | str], ...]:
    return tuple((0, int(part)) if part.isdigit() else (1, part) for part in re.split(r"(\d+)", name.casefold()) if part != "")
