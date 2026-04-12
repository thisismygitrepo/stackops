from machineconfig.scripts.python.ai.scripts import (
    COMMAND_RUNNER_PS1_PATH_REFERENCE,
    COMMAND_RUNNER_SH_PATH_REFERENCE,
    LINT_AND_TYPE_CHECK_PS1_PATH_REFERENCE,
    LINT_AND_TYPE_CHECK_SH_PATH_REFERENCE,
    LINT_AND_TYPE_CHECK_V0_PATH_REFERENCE,
)


def test_script_path_constants_match_expected_script_names() -> None:
    assert COMMAND_RUNNER_PS1_PATH_REFERENCE == "command_runner.ps1"
    assert COMMAND_RUNNER_SH_PATH_REFERENCE == "command_runner.sh"
    assert LINT_AND_TYPE_CHECK_PS1_PATH_REFERENCE == "lint_and_type_check.ps1"
    assert LINT_AND_TYPE_CHECK_SH_PATH_REFERENCE == "lint_and_type_check.sh"
    assert LINT_AND_TYPE_CHECK_V0_PATH_REFERENCE == "lint_and_type_check_v0.sh"
