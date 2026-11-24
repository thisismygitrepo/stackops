import shutil
import subprocess
from pathlib import Path
from platform import system
from typing import Literal, TypedDict

from stackops.scripts.python.helpers.helpers_webui.terminal_ghostty_constants import GHOSTTY_COMMAND, GHOSTTY_MACOS_APP_PATHS, GHOSTTY_SETTINGS_TIMEOUT_SECONDS

# How Ghostty prints a pair of themes that follows the system's appearance: `theme = light:NAME,dark:NAME`.
PAIR_LIGHT_PREFIX = "light:"
PAIR_DARK_MARK = ",dark:"


# The theme Ghostty is set to use in each appearance of the system: one name twice for a single theme, two names for a pair, both empty when no
# theme is set.
class GhosttyTheme(TypedDict):
    light: str
    dark: str


# `ready`: the `ghostty` command runs here. `missing`: there is no Ghostty. `unreachable`: the macOS app is at `app`, but its command is not on
# PATH, and the CLI sets a theme through that command. `theme` is None where it was not read.
class GhosttyStatus(TypedDict):
    state: Literal["ready", "missing", "unreachable"]
    app: str
    theme: GhosttyTheme | None


def read_ghostty_status() -> GhosttyStatus:
    executable = shutil.which(GHOSTTY_COMMAND)
    if executable is None:
        apps = [path for path in (Path(text).expanduser() for text in GHOSTTY_MACOS_APP_PATHS) if path.is_dir()] if system() == "Darwin" else []
        return {"state": "unreachable" if apps else "missing", "app": str(apps[0]) if apps else "", "theme": None}
    # Design choice: the theme is taken from the settings Ghostty itself reports, not from the file StackOps writes, so one set by hand in any
    # of Ghostty's config files counts too. A Ghostty that does not answer leaves the theme out; the rest of the sheet does not depend on it.
    try:
        answer = subprocess.run(
            [executable, "+show-config"], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False, stdin=subprocess.DEVNULL, timeout=GHOSTTY_SETTINGS_TIMEOUT_SECONDS
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"state": "ready", "app": "", "theme": None}
    if answer.returncode != 0:
        return {"state": "ready", "app": "", "theme": None}
    light = dark = ""
    for line in answer.stdout.splitlines():
        key, _, value = line.partition("=")
        if key.strip() != "theme":
            continue
        light = dark = value.strip()
        if light.startswith(PAIR_LIGHT_PREFIX) and PAIR_DARK_MARK in light:
            light, dark = light.removeprefix(PAIR_LIGHT_PREFIX).split(PAIR_DARK_MARK, maxsplit=1)
    return {"state": "ready", "app": "", "theme": {"light": light, "dark": dark}}
