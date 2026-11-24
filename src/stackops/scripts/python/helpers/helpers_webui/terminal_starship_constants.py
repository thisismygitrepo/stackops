from typing import Final

STARSHIP_SETTINGS_FILE_NAME: Final[str] = "starship.toml"
# The programs the command's picker can show its list with, in the order it looks for them.
STARSHIP_PICKER_TOOLS: Final[tuple[str, ...]] = ("tv", "fzf")
STARSHIP_ANSWER_TIMEOUT_SECONDS: Final[float] = 10.0
