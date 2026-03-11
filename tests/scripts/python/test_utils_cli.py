from typer.main import get_command
from typer.testing import CliRunner

from machineconfig.scripts.python.utils import get_app, inspect_utils_help_emojis


runner = CliRunner()


def test_utils_command_aliases_include_single_letter_and_legacy_names() -> None:
    command = get_command(get_app())
    expected_aliases = {
        "k",
        "v",
        "a",
        "up",
        "d",
        "g",
        "i",
        "e",
        "m",
        "pm",
        "c",
        "pc",
        "t",
        "r",
        "db",
    }

    assert expected_aliases.issubset(command.commands)


def test_utils_visible_commands_are_grouped_by_related_tasks() -> None:
    command = get_command(get_app())
    visible_names = [name for name, subcommand in command.commands.items() if not subcommand.hidden]

    assert visible_names == [
        "kill-process",
        "environment",
        "get-machine-specs",
        "init-project",
        "upgrade-packages",
        "type-hint",
        "edit",
        "download",
        "pdf-merge",
        "pdf-compress",
        "read-db",
    ]


def test_utils_help_renders_single_letter_shortcuts() -> None:
    result = runner.invoke(get_app(), ["--help"], terminal_width=220)

    assert result.exit_code == 0
    assert "⚙ utilities operations" in result.stdout
    assert "↑ <a> Upgrade project dependencies." in result.stdout
    assert "◫ <m> Merge two PDF files into one." in result.stdout
    assert "↧ <c> Compress a PDF file." in result.stdout
    assert "🗃 <r> TUI DB Visualizer." in result.stdout


def test_utils_help_glyphs_are_single_width() -> None:
    diagnostics = inspect_utils_help_emojis()

    assert diagnostics
    assert all(not item["has_variation_selector_16"] for item in diagnostics)
    assert all(item["terminal_width"] == 1 for item in diagnostics)
