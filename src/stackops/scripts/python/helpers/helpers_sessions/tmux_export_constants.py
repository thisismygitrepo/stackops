from typing import Final, Literal, TypeAlias

TERMINAL_EXPORT_DEFAULT_BACKEND: Final = "tmux"
TERMINAL_EXPORT_DEFAULT_COMMAND_SOURCE: Final = "shell"
TMUX_EXPORT_DEFAULT_FILENAME = "tmux_export_layout.yaml"
TMUX_EXPORT_SHELL_COMMAND = """sh -lc 'exec "${SHELL:-/bin/sh}"'"""

TmuxExportCommandSource: TypeAlias = Literal[
    "shell",
    "current-command",
    "start-command",
]
