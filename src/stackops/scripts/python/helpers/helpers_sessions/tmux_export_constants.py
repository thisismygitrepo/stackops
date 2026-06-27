from typing import Literal, TypeAlias

TMUX_EXPORT_DEFAULT_FILENAME = "tmux_export_layout.json"
TMUX_EXPORT_LAYOUT_VERSION: Literal["0.1"] = "0.1"
TMUX_EXPORT_SHELL_COMMAND = """sh -lc 'exec "${SHELL:-/bin/sh}"'"""

TmuxExportCommandSource: TypeAlias = Literal[
    "shell",
    "current-command",
    "start-command",
]
