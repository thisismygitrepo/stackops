import re
from typing import Final, Literal

type ShellId = Literal["zsh", "bash", "nushell", "pwsh"]
# Whose syntax a setup script is written in, which decides how its short commands are read.
type ShellFamily = Literal["posix", "nushell", "pwsh"]
# How a shell gets set up from the page: by one of the command's two choices, by hand because the command only acts on the login shell, or not at all.
type SetupRoute = Literal["default", "nushell", "manual", "none"]
type SetupBlocker = Literal["", "not_installed", "other_system"]

SHELL_PROGRAMS: Final[dict[ShellId, str]] = {"zsh": "zsh", "bash": "bash", "nushell": "nu", "pwsh": "pwsh"}
# Nushell has no command that reads its settings again, so the shell is started afresh in the same window.
NUSHELL_RELOAD_COMMAND: Final[str] = "exec nu"

# The parts of StackOps' shell setup, by the words that switch each one on in a setup script, and the program a part needs. A part with several
# programs uses the first one that is installed, in the order the script names them. The last part needs no program.
SHELL_EXTRAS: Final[tuple[tuple[str, str, re.Pattern[str]], ...]] = (
    ("prompt", "starship", re.compile(r"\bstarship\b")),
    ("jump", "zoxide", re.compile(r"\bzoxide\b")),
    ("history", "mcfly", re.compile(r"\bmcfly\b")),
    ("history", "atuin", re.compile(r"\batuin\b")),
    ("history", "tv", re.compile(r"\btv\s+\S*history")),
    ("browse", "yazi", re.compile(r"\byazi")),
    ("listing", "lsd", re.compile(r"\blsd\b")),
    ("path", "", re.compile(r"add[-_]?to[-_]?path|\bpath add\b", re.IGNORECASE)),
)

# The helper every short command of StackOps' own tools goes through, and what PowerShell adds around a command's name.
ALIAS_WRAPPER: Final[str] = "wrap_in_shell_script "
NUSHELL_ALIAS: Final[re.Pattern[str]] = re.compile(r"(?:export\s+)?alias\s+(?P<name>\S+)\s*=\s*\^?(?P<runs>.+)")
PWSH_FUNCTION: Final[re.Pattern[str]] = re.compile(r"function\s+(?P<name>[\w-]+)\s*\{\s*(?P<runs>[^{}]+?)\s*\}")
PWSH_ALIAS: Final[re.Pattern[str]] = re.compile(r"Set-Alias\s+-Name\s+(?P<name>\S+)\s+-Value\s+(?P<runs>\S+)")
PWSH_NOISE: Final[re.Pattern[str]] = re.compile(r"\.exe\b|\s*[@$]args\b")
