from dataclasses import dataclass
import os
from pathlib import Path
import shutil
from typing import assert_never

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import (
    CHROMIUM_PROFILE_CLEANUP_PATHS,
    CHROMIUM_USER_DATA_CLEANUP_PATHS,
    FIREFOX_PROFILE_CLEANUP_PATHS,
    TEMPORARY_BROWSER_PROFILE_DIRECTORY_NAME,
    BrowserName,
    ProfileBrowserName,
)
from stackops.scripts.python.helpers.helpers_agents.agents_browser_detached_processes import find_browser_profile_process_ids
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_lock import browser_launch_lock
from stackops.scripts.python.helpers.helpers_agents.agents_browser_profile_filesystem import (
    copy_directory_tree_excluding,
    directory_size_bytes,
    remove_owned_profile_directories,
    require_tree_without_filesystem_boundaries,
)
from stackops.scripts.python.helpers.helpers_agents.agents_browser_profile_listing import list_browser_profile_paths
from stackops.scripts.python.helpers.helpers_agents.agents_browser_resolution import resolve_named_profile_path


@dataclass(frozen=True, slots=True)
class BrowserProfileDeclutterResult:
    browser: BrowserName
    profile_path: Path
    removed_paths: tuple[Path, ...]
    size_before_bytes: int
    size_after_bytes: int
    recovered_bytes: int


@dataclass(frozen=True, slots=True)
class BrowserProfileReplicationResult:
    browser: BrowserName
    source_path: Path
    destination_paths: tuple[Path, ...]
    source_size_bytes: int


def declutter_browser_profile(*, browser: BrowserName, profile_name: str) -> BrowserProfileDeclutterResult:
    profile_path = resolve_named_profile_path(browser=browser, profile_name=profile_name)
    with browser_launch_lock():
        require_browser_profile_directory(profile_path=profile_path)
        require_browser_profile_not_in_use(browser=browser, profile_path=profile_path)
        excluded_root_directory_names = frozenset({TEMPORARY_BROWSER_PROFILE_DIRECTORY_NAME})
        size_before_bytes = directory_size_bytes(directory=profile_path, excluded_root_directory_names=excluded_root_directory_names)
        cleanup_paths = _resolve_cleanup_paths(browser=browser, profile_path=profile_path)
        existing_cleanup_paths = tuple(path for path in cleanup_paths if path.exists() or path.is_symlink())
        for cleanup_path in existing_cleanup_paths:
            if cleanup_path.is_dir() and not cleanup_path.is_symlink() and not cleanup_path.is_junction():
                require_tree_without_filesystem_boundaries(directory=cleanup_path, include_root=True, excluded_root_directory_names=frozenset())
        removed_paths: list[Path] = []
        for cleanup_path in existing_cleanup_paths:
            try:
                if cleanup_path.is_junction():
                    cleanup_path.rmdir()
                elif cleanup_path.is_dir() and not cleanup_path.is_symlink():
                    shutil.rmtree(cleanup_path)
                else:
                    cleanup_path.unlink()
            except OSError as error:
                raise RuntimeError(f"""Could not remove browser profile data at {cleanup_path}: {error}""") from error
            removed_paths.append(cleanup_path)
        size_after_bytes = directory_size_bytes(directory=profile_path, excluded_root_directory_names=excluded_root_directory_names)
    return BrowserProfileDeclutterResult(
        browser=browser,
        profile_path=profile_path,
        removed_paths=tuple(removed_paths),
        size_before_bytes=size_before_bytes,
        size_after_bytes=size_after_bytes,
        recovered_bytes=size_before_bytes - size_after_bytes,
    )


def declutter_all_browser_profiles(*, browser: ProfileBrowserName) -> tuple[BrowserProfileDeclutterResult, ...]:
    profile_paths = list_browser_profile_paths(browser=browser)
    return tuple(declutter_browser_profile(browser=browser, profile_name=profile_path.name) for profile_path in profile_paths)


def replicate_browser_profile(*, browser: BrowserName, profile_name: str, count: int, overwrite: bool) -> BrowserProfileReplicationResult:
    if count < 1:
        raise ValueError("COUNT must be at least 1")
    source_path = resolve_named_profile_path(browser=browser, profile_name=profile_name)
    destination_paths = tuple(resolve_named_profile_path(browser=browser, profile_name=f"p{index}") for index in range(1, count + 1))
    source_path_key = os.path.normcase(str(source_path))
    if any(os.path.normcase(str(destination_path)) == source_path_key for destination_path in destination_paths):
        raise ValueError(f"""Source profile must not be one of the replication destinations: {source_path}""")
    with browser_launch_lock():
        require_browser_profile_directory(profile_path=source_path)
        require_browser_profile_not_in_use(browser=browser, profile_path=source_path)
        excluded_root_directory_names = frozenset({TEMPORARY_BROWSER_PROFILE_DIRECTORY_NAME})
        require_tree_without_filesystem_boundaries(
            directory=source_path, include_root=False, excluded_root_directory_names=excluded_root_directory_names
        )
        collisions = tuple(path for path in destination_paths if path.exists() or path.is_symlink())
        if overwrite:
            _remove_existing_destination_profiles(browser=browser, destination_paths=collisions)
        elif len(collisions) > 0:
            collision_list = ", ".join(str(path) for path in collisions)
            raise ValueError(f"""Refusing to overwrite existing browser profile copies: {collision_list}. Pass --overwrite to replace them.""")
        source_size_bytes = directory_size_bytes(directory=source_path, excluded_root_directory_names=excluded_root_directory_names)
        reserved_paths: list[Path] = []
        destination_path = destination_paths[0]
        try:
            for destination_path in destination_paths:
                reserved_paths.append(destination_path)
                try:
                    destination_path.mkdir()
                except FileExistsError:
                    reserved_paths.pop()
                    raise
            for destination_path in destination_paths:
                copy_directory_tree_excluding(
                    source_directory=source_path, destination_directory=destination_path, excluded_root_directory_names=excluded_root_directory_names
                )
        except BaseException as error:
            cleanup_failures = remove_owned_profile_directories(directories=tuple(reserved_paths))
            if isinstance(error, OSError):
                cleanup_note = "" if len(cleanup_failures) == 0 else f" Rollback failures: {'; '.join(cleanup_failures)}"
                raise RuntimeError(f"""Could not replicate browser profile to {destination_path}: {error}.{cleanup_note}""") from error
            for cleanup_failure in cleanup_failures:
                error.add_note(f"""Browser profile rollback failed: {cleanup_failure}""")
            raise
    return BrowserProfileReplicationResult(
        browser=browser, source_path=source_path, destination_paths=destination_paths, source_size_bytes=source_size_bytes
    )


def require_browser_profile_directory(*, profile_path: Path) -> None:
    if not profile_path.is_dir():
        raise ValueError(f"""Browser profile does not exist or is not a directory: {profile_path}""")
    if profile_path.is_symlink() or profile_path.is_junction():
        raise ValueError(f"""Browser profile must not be a symbolic link or junction: {profile_path}""")
    profiles_root = profile_path.parents[1]
    try:
        if not profile_path.resolve(strict=True).is_relative_to(profiles_root.resolve(strict=True)):
            raise ValueError(f"""Browser profile resolves outside the StackOps profiles root: {profile_path}""")
    except OSError as error:
        raise RuntimeError(f"""Could not resolve browser profile path {profile_path}: {error}""") from error


def require_browser_profile_not_in_use(*, browser: BrowserName, profile_path: Path) -> None:
    process_ids = find_browser_profile_process_ids(browser=browser, profile_path=profile_path)
    if len(process_ids) > 0:
        process_list = ", ".join(str(process_id) for process_id in process_ids)
        raise RuntimeError(
            f"""The selected browser is running under process ID(s) {process_list}. Close it before changing profile: {profile_path}"""
        )


def _remove_existing_destination_profiles(*, browser: BrowserName, destination_paths: tuple[Path, ...]) -> None:
    for destination_path in destination_paths:
        require_browser_profile_directory(profile_path=destination_path)
        require_browser_profile_not_in_use(browser=browser, profile_path=destination_path)
        require_tree_without_filesystem_boundaries(directory=destination_path, include_root=True, excluded_root_directory_names=frozenset())
    for destination_path in destination_paths:
        try:
            shutil.rmtree(destination_path)
        except OSError as error:
            raise RuntimeError(f"""Could not remove existing browser profile copy {destination_path}: {error}""") from error


def _resolve_cleanup_paths(*, browser: BrowserName, profile_path: Path) -> tuple[Path, ...]:
    match browser:
        case "chrome" | "brave" | "edge":
            cleanup_paths = [profile_path.joinpath(*relative_path) for relative_path in CHROMIUM_USER_DATA_CLEANUP_PATHS]
            profile_roots = [profile_path]
            try:
                profile_roots.extend(
                    child
                    for child in profile_path.iterdir()
                    if child.is_dir()
                    and not child.is_symlink()
                    and not child.is_junction()
                    and _is_chromium_profile_directory_name(directory_name=child.name)
                )
            except OSError as error:
                raise RuntimeError(f"""Could not inspect browser profile directory {profile_path}: {error}""") from error
            cleanup_paths.extend(
                profile_root.joinpath(*relative_path) for profile_root in profile_roots for relative_path in CHROMIUM_PROFILE_CLEANUP_PATHS
            )
            return tuple(dict.fromkeys(cleanup_paths))
        case "firefox":
            return tuple(profile_path.joinpath(*relative_path) for relative_path in FIREFOX_PROFILE_CLEANUP_PATHS)
        case "safari":
            raise ValueError("Safari does not support StackOps browser profiles")
        case _:
            assert_never(browser)


def _is_chromium_profile_directory_name(*, directory_name: str) -> bool:
    return directory_name in {"Default", "Guest Profile", "System Profile"} or directory_name.startswith("Profile ")
