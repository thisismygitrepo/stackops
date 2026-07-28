from typer.testing import CliRunner

from stackops.scripts.python.helpers.helpers_devops.cli_repos import get_app


def test_action_help_includes_status_option() -> None:
    result = CliRunner().invoke(get_app(), ["a", "--help"], terminal_width=180)

    assert result.exit_code == 0
    assert "--status" in result.output
    assert "-s" in result.output
    assert "Show status across repositories." in result.output
