"""Utility commands - lazy loading nested subcommands."""

from typing import TYPE_CHECKING

import typer

if TYPE_CHECKING:
    from machineconfig.scripts.python.devops import EmojiDisplayDiagnostic


UTILS_HELP_GLYPHS: list[str] = [
    "⚙",
    "🖥",
    "⚔",
    "⌘",
    "💽",
    "🔌",
    "🐍",
    "✦",
    "↑",
    "✐",
    "📁",
    "✏",
    "↓",
    "◫",
    "↧",
    "🗃",
]


def inspect_utils_help_emojis() -> list["EmojiDisplayDiagnostic"]:
    from machineconfig.scripts.python.devops import emoji_display_diagnostics

    return emoji_display_diagnostics(UTILS_HELP_GLYPHS)


def get_app() -> typer.Typer:
    app = typer.Typer(help="⚙ utilities operations", no_args_is_help=True, add_help_option=True, add_completion=False)
    from machineconfig.scripts.python.helpers.helpers_utils.file_utils_app import get_app as get_file_app
    from machineconfig.scripts.python.helpers.helpers_utils.machine_utils_app import get_app as get_machine_app
    from machineconfig.scripts.python.helpers.helpers_utils.pyproject_utils_app import get_app as get_pyproject_app

    app.add_typer(get_machine_app(), name="machine", help="🖥 <m> Machine and device utilities")
    app.add_typer(get_machine_app(), name="m", help="Machine and device utilities", hidden=True)
    app.add_typer(get_pyproject_app(), name="pyproject", help="🐍 <p> Pyproject bootstrap and typing utilities")
    app.add_typer(get_pyproject_app(), name="p", help="Pyproject bootstrap and typing utilities", hidden=True)
    app.add_typer(get_file_app(), name="file", help="📁 <f> File, document, and database utilities")
    app.add_typer(get_file_app(), name="f", help="File, document, and database utilities", hidden=True)
    return app


def main() -> None:
    app = get_app()
    app()


if __name__ == "__main__":
    main()
