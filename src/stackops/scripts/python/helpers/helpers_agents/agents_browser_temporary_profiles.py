from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import (
    TEMPORARY_BROWSER_PROFILE_ALIAS_ATTEMPTS,
    TEMPORARY_BROWSER_PROFILE_DIRECTORY_NAME,
    BrowserName,
)
from stackops.scripts.python.helpers.helpers_agents.agents_browser_profile_filesystem import (
    copy_directory_tree_excluding,
    path_is_filesystem_boundary,
    remove_owned_profile_directories,
    require_tree_without_filesystem_boundaries,
)
from stackops.scripts.python.helpers.helpers_agents.agents_browser_profiles import (
    require_browser_profile_directory,
    require_browser_profile_not_in_use,
)
from stackops.utils.accessories import randstr


def copy_browser_profile_to_temporary(*, browser: BrowserName, source_path: Path) -> Path:
    require_browser_profile_directory(profile_path=source_path)
    require_browser_profile_not_in_use(browser=browser, profile_path=source_path)
    excluded_root_directory_names = frozenset({TEMPORARY_BROWSER_PROFILE_DIRECTORY_NAME})
    require_tree_without_filesystem_boundaries(directory=source_path, include_root=False, excluded_root_directory_names=excluded_root_directory_names)
    temporary_root = source_path.joinpath(TEMPORARY_BROWSER_PROFILE_DIRECTORY_NAME)
    _prepare_temporary_root(temporary_root=temporary_root)
    return _copy_to_random_alias(source_path=source_path, temporary_root=temporary_root, excluded_root_directory_names=excluded_root_directory_names)


def _prepare_temporary_root(*, temporary_root: Path) -> None:
    try:
        temporary_root.mkdir()
    except FileExistsError:
        if not temporary_root.is_dir() or temporary_root.is_symlink() or temporary_root.is_junction():
            raise ValueError(f"Temporary browser profile root must be a regular directory: {temporary_root}") from None
    except OSError as error:
        raise RuntimeError(f"Could not create temporary browser profile root {temporary_root}: {error}") from error
    if path_is_filesystem_boundary(path=temporary_root):
        raise ValueError(f"Temporary browser profile root must not be a filesystem boundary: {temporary_root}")


def _copy_to_random_alias(*, source_path: Path, temporary_root: Path, excluded_root_directory_names: frozenset[str]) -> Path:
    for _attempt in range(TEMPORARY_BROWSER_PROFILE_ALIAS_ATTEMPTS):
        alias_name = randstr(noun=True)
        if alias_name in {"", ".", "..", TEMPORARY_BROWSER_PROFILE_DIRECTORY_NAME} or any(
            invalid_character in alias_name for invalid_character in ("/", "\\", ":", "*", "?", '"', "<", ">", "|")
        ):
            raise RuntimeError(f"Random browser profile alias is not a valid directory name: {alias_name!r}")
        destination_path = temporary_root.joinpath(alias_name)
        try:
            try:
                destination_path.mkdir()
            except FileExistsError:
                continue
            copy_directory_tree_excluding(
                source_directory=source_path, destination_directory=destination_path, excluded_root_directory_names=excluded_root_directory_names
            )
            return destination_path
        except BaseException as error:
            cleanup_failures = remove_owned_profile_directories(directories=(destination_path,))
            if isinstance(error, OSError):
                cleanup_note = "" if len(cleanup_failures) == 0 else f" Rollback failures: {'; '.join(cleanup_failures)}"
                raise RuntimeError(f"Could not copy browser profile to {destination_path}: {error}.{cleanup_note}") from error
            for cleanup_failure in cleanup_failures:
                error.add_note(f"Browser profile rollback failed: {cleanup_failure}")
            raise
    raise RuntimeError(
        f"Could not reserve a unique temporary browser profile after {TEMPORARY_BROWSER_PROFILE_ALIAS_ATTEMPTS} aliases under {temporary_root}"
    )
