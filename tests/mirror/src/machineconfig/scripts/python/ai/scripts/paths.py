from pathlib import Path

from machineconfig.scripts.python.ai.scripts import LINT_AND_TYPE_CHECK_PATH_REFERENCE
from machineconfig.scripts.python.ai.scripts.paths import (
	LINT_AND_TYPE_CHECK_REPO_RELATIVE_PATH,
	TYPE_CHECKING_SCRIPT_PATH_REFERENCES,
	TYPE_CHECKING_SCRIPTS_DIRECTORY,
)


def test_type_checking_paths_match_expected_repo_layout() -> None:
	assert TYPE_CHECKING_SCRIPTS_DIRECTORY == Path("scripts").joinpath("type_checking")
	assert TYPE_CHECKING_SCRIPT_PATH_REFERENCES == (
		"lint_and_type_check.py",
		"models.py",
		"dashboard.py",
	)
	assert LINT_AND_TYPE_CHECK_REPO_RELATIVE_PATH == TYPE_CHECKING_SCRIPTS_DIRECTORY.joinpath(
		LINT_AND_TYPE_CHECK_PATH_REFERENCE
	)