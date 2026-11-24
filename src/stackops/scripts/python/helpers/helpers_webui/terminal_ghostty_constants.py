from typing import Final

GHOSTTY_COMMAND: Final[str] = "ghostty"
# Ghostty prints its settings in a fraction of a second. One that takes this long is left out of the answer, so the sheet is never left waiting.
GHOSTTY_SETTINGS_TIMEOUT_SECONDS: Final[float] = 5.0
# Where the macOS app sits when it was dragged in by hand. Its command is then on PATH only inside Ghostty's own windows, so a StackOps started
# elsewhere finds the app but cannot run it by name.
GHOSTTY_MACOS_APP_PATHS: Final[tuple[str, ...]] = ("/Applications/Ghostty.app", "~/Applications/Ghostty.app")
