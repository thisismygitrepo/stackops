from typer.testing import CliRunner

from stackops.scripts.python.helpers.helpers_utils.pyproject_utils_app import get_app


def test_help_lists_test_runtime_command() -> None:
    result = CliRunner().invoke(get_app(), ["--help"])

    assert result.exit_code == 0
    assert "test-runtime" in result.stdout
    assert "runtime-test workflow" in result.stdout
