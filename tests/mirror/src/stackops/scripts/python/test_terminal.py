import subprocess
import sys

import pytest
from typer.testing import CliRunner

from stackops.scripts.python import terminal
from stackops.scripts.python.terminal_summary_models import LegacySummarizeBackend, SummarizeVocabulary, SummaryBackend


@pytest.mark.parametrize("arguments", [("--help",), ("summary", "--help"), ("s", "--help"), ("summarize", "--help"), ("S", "--help")])
def test_terminal_help_does_not_import_summary_implementations(arguments: tuple[str, ...]) -> None:
    script = """import sys
from typer.testing import CliRunner
from stackops.scripts.python import terminal

result = CliRunner().invoke(terminal.get_app(), sys.argv[1:])
assert result.exit_code == 0, result.output
blocked_modules = (
    "stackops.scripts.python.terminal_summary",
    "stackops.scripts.python.terminal_summarize",
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
        ((), ("tmux", None, False, False)),
        (("-b", "tuios", "-s", "sample", "-t"), ("tuios", "sample", False, True)),
        (("-c",), ("tmux", None, True, False)),
    ],
)
def test_summary_command_forwards_defaults_and_options(
    command: str,
    arguments: tuple[str, ...],
    expected_values: tuple[SummaryBackend, str | None, bool, bool],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from stackops.scripts.python import terminal_summary

    captured_values: list[tuple[SummaryBackend, str | None, bool, bool]] = []

    def capture_summary(*, backend: SummaryBackend, session: str | None, choose_session: bool, show_tabs: bool) -> None:
        captured_values.append((backend, session, choose_session, show_tabs))

    monkeypatch.setattr(terminal_summary, "summary", capture_summary)

    result = CliRunner().invoke(terminal.get_app(), [command, *arguments])

    assert result.exit_code == 0, result.output
    assert captured_values == [expected_values]


@pytest.mark.parametrize("command", ["summarize", "S"])
def test_summarize_command_forwards_options(command: str, monkeypatch: pytest.MonkeyPatch) -> None:
    from stackops.scripts.python import terminal_summarize

    captured_values: list[tuple[str, SummarizeVocabulary, LegacySummarizeBackend | None, bool]] = []

    def capture_summary(*, layout_path: str, vocabulary: SummarizeVocabulary, backend: LegacySummarizeBackend | None, show_tabs: bool) -> None:
        captured_values.append((layout_path, vocabulary, backend, show_tabs))

    monkeypatch.setattr(terminal_summarize, "summarize", capture_summary)

    result = CliRunner().invoke(terminal.get_app(), [command, "layout.json", "-v", "herdr", "-t"])

    assert result.exit_code == 0, result.output
    assert captured_values == [("layout.json", "herdr", None, True)]
