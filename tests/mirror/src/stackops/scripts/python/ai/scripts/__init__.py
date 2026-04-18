from stackops.scripts.python.ai.scripts import (
    DASHBOARD_PATH_REFERENCE,
    LINT_AND_TYPE_CHECK_PATH_REFERENCE,
    MODEL_PATH_REFERENCE,
)


def test_script_path_constants_match_expected_script_names() -> None:
    assert LINT_AND_TYPE_CHECK_PATH_REFERENCE == "lint_and_type_check.py"
    assert MODEL_PATH_REFERENCE == "models.py"
    assert DASHBOARD_PATH_REFERENCE == "dashboard.py"
