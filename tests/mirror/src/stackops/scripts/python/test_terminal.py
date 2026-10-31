import subprocess
import sys

import pytest
from typer.testing import CliRunner

from stackops.scripts.python import terminal
from stackops.utils.schemas.config.multiplexer_types import SessionMultiplexerOption


@pytest.mark.parametrize("arguments", [("--help",), ("summary", "--help"), ("s", "--help")])
def test_terminal_help_does_not_import_summary_implementations(arguments: tuple[str, ...]) -> None:
    script = """import sys
from typer.testing import CliRunner
from stackops.scripts.python import terminal

result = CliRunner().invoke(terminal.get_app(), sys.argv[1:])
assert result.exit_code == 0, result.output
blocked_modules = (
    "stackops.scripts.python.terminal_summary",
    "stackops.scripts.python.helpers.helpers_sessions._tmux_backend",
    "stackops.scripts.python.helpers.helpers_sessions._herdr_backend",
    "stackops.scripts.python.helpers.helpers_sessions._aoe_backend",
    "stackops.scripts.python.helpers.helpers_sessions.tuios_summary",
)
loaded_modules = tuple(name for name in blocked_modules if name in sys.modules)
assert not loaded_modules, loaded_modules
"""

    result = subprocess.run([sys.executable, "-c", script, *arguments], check=False, capture_output=True, text=True)

    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("command", ["summary", "s"])
@pytest.mark.parametrize(
    ("arguments", "expected_values"),
    [
        ((), (None, None, False, False)),
        (("-b", "tuios", "-s", "sample", "-t"), ("tuios", "sample", False, True)),
        (("-c",), (None, None, True, False)),
    ],
)
def test_summary_command_forwards_defaults_and_options(
    command: str,
    arguments: tuple[str, ...],
    expected_values: tuple[SessionMultiplexerOption | None, str | None, bool, bool],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from stackops.scripts.python import terminal_summary

    captured_values: list[tuple[SessionMultiplexerOption | None, str | None, bool, bool]] = []

    def capture_summary(*, backend: SessionMultiplexerOption | None, session: str | None, choose_session: bool, show_tabs: bool) -> None:
        captured_values.append((backend, session, choose_session, show_tabs))

    monkeypatch.setattr(terminal_summary, "summary", capture_summary)

    result = CliRunner().invoke(terminal.get_app(), [command, *arguments])

    assert result.exit_code == 0, result.output
    assert captured_values == [expected_values]
