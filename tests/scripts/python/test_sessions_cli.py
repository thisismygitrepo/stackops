from typer.main import get_command
from typer.testing import CliRunner

from machineconfig.scripts.python.sessions import get_app


runner = CliRunner()


def test_sessions_command_aliases_include_kill() -> None:
    command = get_command(get_app())

    assert "kill" in command.commands
    assert "k" in command.commands


def test_sessions_kill_help_mentions_window_targets() -> None:
    result = runner.invoke(get_app(), ["kill", "--help"], terminal_width=220)

    assert result.exit_code == 0
    assert "--window" in result.stdout
    assert "Choose one or more session targets to kill." in result.stdout
