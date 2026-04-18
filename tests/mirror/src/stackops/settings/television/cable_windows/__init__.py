from pathlib import Path

import pytest

from stackops.settings.television import cable_windows

_PATH_REFERENCES: tuple[tuple[str, str], ...] = (
    ("ALIAS_PATH_REFERENCE", cable_windows.ALIAS_PATH_REFERENCE),
    ("DIRS_PATH_REFERENCE", cable_windows.DIRS_PATH_REFERENCE),
    ("DOCKER_IMAGES_PATH_REFERENCE", cable_windows.DOCKER_IMAGES_PATH_REFERENCE),
    ("DOTFILES_PATH_REFERENCE", cable_windows.DOTFILES_PATH_REFERENCE),
    ("ENV_PATH_REFERENCE", cable_windows.ENV_PATH_REFERENCE),
    ("FILES_PATH_REFERENCE", cable_windows.FILES_PATH_REFERENCE),
    ("GIT_BRANCH_PATH_REFERENCE", cable_windows.GIT_BRANCH_PATH_REFERENCE),
    ("GIT_DIFF_PATH_REFERENCE", cable_windows.GIT_DIFF_PATH_REFERENCE),
    ("GIT_LOG_PATH_REFERENCE", cable_windows.GIT_LOG_PATH_REFERENCE),
    ("GIT_REFLOG_PATH_REFERENCE", cable_windows.GIT_REFLOG_PATH_REFERENCE),
    ("GIT_REPOS_PATH_REFERENCE", cable_windows.GIT_REPOS_PATH_REFERENCE),
    ("NU_HISTORY_PATH_REFERENCE", cable_windows.NU_HISTORY_PATH_REFERENCE),
    ("PWSH_HISTORY_PATH_REFERENCE", cable_windows.PWSH_HISTORY_PATH_REFERENCE),
    ("TEXT_PATH_REFERENCE", cable_windows.TEXT_PATH_REFERENCE),
)


def _assert_local_reference(module_dir: Path, constant_name: str, relative_path: str) -> None:
    reference_path = Path(relative_path)
    assert not reference_path.is_absolute(), constant_name
    assert reference_path == Path(reference_path.name), constant_name
    assert (module_dir / reference_path).is_file(), constant_name


@pytest.mark.parametrize(("constant_name", "relative_path"), _PATH_REFERENCES)
def test_path_references_point_to_existing_local_files(constant_name: str, relative_path: str) -> None:
    module_dir = Path(cable_windows.__file__).resolve().parent
    _assert_local_reference(module_dir, constant_name, relative_path)
