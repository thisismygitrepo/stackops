from __future__ import annotations

from pathlib import PurePosixPath

from machineconfig.utils.ssh_utils import abc as sut


def test_machineconfig_version_uses_expected_constraint_prefix() -> None:
    package_name, version = sut.MACHINECONFIG_VERSION.split(">=", maxsplit=1)
    assert package_name == "machineconfig"
    assert version != ""


def test_default_pickle_subdir_is_relative_nested_path() -> None:
    rel_path = PurePosixPath(sut.DEFAULT_PICKLE_SUBDIR)
    assert not rel_path.is_absolute()
    assert rel_path.parts[:2] == ("tmp_results", "tmp_scripts")
    assert rel_path.parts[-1] == "ssh"
