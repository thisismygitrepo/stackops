from pathlib import Path

import pytest

from machineconfig.settings.television import cable_unix

_PATH_REFERENCES: tuple[tuple[str, str], ...] = (
    ("ALIAS_PATH_REFERENCE", cable_unix.ALIAS_PATH_REFERENCE),
    ("AWS_BUCKETS_PATH_REFERENCE", cable_unix.AWS_BUCKETS_PATH_REFERENCE),
    ("AWS_INSTANCES_PATH_REFERENCE", cable_unix.AWS_INSTANCES_PATH_REFERENCE),
    ("BASH_HISTORY_PATH_REFERENCE", cable_unix.BASH_HISTORY_PATH_REFERENCE),
    ("CHANNELS_PATH_REFERENCE", cable_unix.CHANNELS_PATH_REFERENCE),
    ("DIRS_PATH_REFERENCE", cable_unix.DIRS_PATH_REFERENCE),
    ("DISTROBOX_LIST_PATH_REFERENCE", cable_unix.DISTROBOX_LIST_PATH_REFERENCE),
    ("DOCKER_IMAGES_PATH_REFERENCE", cable_unix.DOCKER_IMAGES_PATH_REFERENCE),
    ("DOTFILES_PATH_REFERENCE", cable_unix.DOTFILES_PATH_REFERENCE),
    ("ENV_PATH_REFERENCE", cable_unix.ENV_PATH_REFERENCE),
    ("FILES_PATH_REFERENCE", cable_unix.FILES_PATH_REFERENCE),
    ("FISH_HISTORY_PATH_REFERENCE", cable_unix.FISH_HISTORY_PATH_REFERENCE),
    ("GIT_BRANCH_PATH_REFERENCE", cable_unix.GIT_BRANCH_PATH_REFERENCE),
    ("GIT_DIFF_PATH_REFERENCE", cable_unix.GIT_DIFF_PATH_REFERENCE),
    ("GIT_LOG_PATH_REFERENCE", cable_unix.GIT_LOG_PATH_REFERENCE),
    ("GIT_REFLOG_PATH_REFERENCE", cable_unix.GIT_REFLOG_PATH_REFERENCE),
    ("GIT_REPOS_PATH_REFERENCE", cable_unix.GIT_REPOS_PATH_REFERENCE),
    ("GUIX_PATH_REFERENCE", cable_unix.GUIX_PATH_REFERENCE),
    ("JUST_RECIPES_PATH_REFERENCE", cable_unix.JUST_RECIPES_PATH_REFERENCE),
    ("K8S_DEPLOYMENTS_PATH_REFERENCE", cable_unix.K8S_DEPLOYMENTS_PATH_REFERENCE),
    ("K8S_PODS_PATH_REFERENCE", cable_unix.K8S_PODS_PATH_REFERENCE),
    ("K8S_SERVICES_PATH_REFERENCE", cable_unix.K8S_SERVICES_PATH_REFERENCE),
    ("MAN_PAGES_PATH_REFERENCE", cable_unix.MAN_PAGES_PATH_REFERENCE),
    ("NU_HISTORY_PATH_REFERENCE", cable_unix.NU_HISTORY_PATH_REFERENCE),
    ("PROCS_PATH_REFERENCE", cable_unix.PROCS_PATH_REFERENCE),
    ("TEXT_PATH_REFERENCE", cable_unix.TEXT_PATH_REFERENCE),
    ("TLDR_PATH_REFERENCE", cable_unix.TLDR_PATH_REFERENCE),
    ("ZSH_HISTORY_PATH_REFERENCE", cable_unix.ZSH_HISTORY_PATH_REFERENCE),
)


def _assert_local_reference(module_dir: Path, constant_name: str, relative_path: str) -> None:
    reference_path = Path(relative_path)
    assert not reference_path.is_absolute(), constant_name
    assert reference_path == Path(reference_path.name), constant_name
    assert (module_dir / reference_path).is_file(), constant_name


@pytest.mark.parametrize(("constant_name", "relative_path"), _PATH_REFERENCES)
def test_path_references_point_to_existing_local_files(constant_name: str, relative_path: str) -> None:
    module_dir = Path(cable_unix.__file__).resolve().parent
    _assert_local_reference(module_dir, constant_name, relative_path)
