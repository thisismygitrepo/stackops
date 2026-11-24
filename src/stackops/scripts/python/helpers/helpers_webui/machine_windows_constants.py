from typing import Final

# The page of System Settings where macOS lists the apps allowed to see and move other apps' windows.
ACCESSIBILITY_SETTINGS_ADDRESS: Final[str] = "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
OPEN_SETTINGS_TIMEOUT_SECONDS: Final[float] = 10.0
# More displays than this are not read; macOS itself drives far fewer.
MAX_DISPLAYS: Final[int] = 16
# The most windows one request may act on, which is far more than a desktop holds.
ACTION_BATCH_LIMIT: Final[int] = 500
# What the page says in place of a macOS Accessibility error number.
ACCESSIBILITY_REFUSAL: Final[str] = "The window does not allow that, or its app is not answering."
MINIMIZE_NEEDS_XDOTOOL: Final[str] = "Minimizing needs the xdotool program, which is not installed on this machine."
