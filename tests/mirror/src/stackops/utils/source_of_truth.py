from __future__ import annotations

from pathlib import Path

import stackops

from stackops.utils import source_of_truth as sut


def test_source_of_truth_points_at_repo_and_library_roots() -> None:
    library_root = Path(stackops.__file__).resolve().parent
    assert sut.LIBRARY_ROOT == library_root
    assert sut.REPO_ROOT == library_root.parent.parent
    assert sut.REPO_ROOT.joinpath("pyproject.toml").is_file()


def test_source_of_truth_library_script_root_exists_inside_repo() -> None:
    assert sut.SCRIPTS_ROOT_LIBRARY.is_dir()
    assert sut.SCRIPTS_ROOT_LIBRARY.is_relative_to(sut.REPO_ROOT)
    assert ".ai" in sut.EXCLUDE_DIRS
    assert ".git" in sut.EXCLUDE_DIRS
