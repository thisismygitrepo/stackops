from pathlib import Path
import re

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import BROWSER_PROFILES_ROOT, ProfileBrowserName


def list_browser_profile_paths(*, browser: ProfileBrowserName) -> tuple[Path, ...]:
    browser_profiles_root = BROWSER_PROFILES_ROOT.expanduser().joinpath(browser)
    if not browser_profiles_root.is_dir():
        raise RuntimeError(f"Browser profiles directory does not exist: {browser_profiles_root}")
    try:
        profile_paths = tuple(
            sorted((path for path in browser_profiles_root.iterdir() if path.is_dir()), key=lambda path: natural_profile_name_key(name=path.name))
        )
    except OSError as error:
        raise RuntimeError(f"Could not read browser profiles directory {browser_profiles_root}: {error}") from error
    if len(profile_paths) == 0:
        raise RuntimeError(f"No browser profiles found under: {browser_profiles_root}")
    return profile_paths


def natural_profile_name_key(*, name: str) -> tuple[tuple[int, int | str], ...]:
    return tuple((0, int(part)) if part.isdigit() else (1, part) for part in re.split(r"(\d+)", name.casefold()) if part != "")
