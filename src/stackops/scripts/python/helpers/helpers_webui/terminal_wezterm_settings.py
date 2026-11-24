import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypedDict, cast

WEZTERM_EXECUTABLE = "wezterm"
# WezTerm reads this file in the home folder before any other (checked against WezTerm 20240203), and the command never looks at it.
HOME_SETTINGS_NAME = ".wezterm.lua"
# The test the command uses to find the lines it rewrites, the same line with Lua's comment mark in front, and such a line that holds nothing
# but one quoted name.
SCHEME_LINE = re.compile(r"""^\s*config\.color_scheme\s*=""")
SWITCHED_OFF_LINE = re.compile(r"""^\s*--+\s*config\.color_scheme\s*=""")
QUOTED_NAME = re.compile(r"""^\s*config\.color_scheme\s*=\s*(?:"([^"\\]+)"|'([^'\\]+)')\s*;?\s*(?:--.*)?$""")

type FileState = Literal["ready", "missing", "unreadable", "no_line", "line_off"]


# Where the WezTerm theme stands on this machine. `names` is the command's own list. `path` is the settings file the command changes, and
# `file` says whether it can: "no_line" has no line that sets the colour scheme, "line_off" has one that is commented out, at `line` (counted
# from 1). `places` counts the lines that set the scheme; the command rewrites every one of them. `current` is the name they hold, or None
# when they disagree or hold something other than a quoted name. `shadow` is a file WezTerm reads in place of `path`, or empty.
class WeztermState(TypedDict):
    installed: bool
    names: list[str]
    path: str
    file: FileState
    current: str | None
    places: int
    line: int | None
    detail: str
    shadow: str


@dataclass(frozen=True)
class WeztermProblem:
    status: int
    message: str


def read_state() -> WeztermState:
    from stackops.scripts.python.helpers.helpers_devops.themes.choose_wezterm_theme import schemes_list
    from stackops.utils.cli_utils.command_lookup import check_tool_exists

    # Where the command looks, word for word: nothing in it tells the path without also writing the file.
    path = Path(os.environ.get("XDG_CONFIG_HOME", "~/.config")).expanduser() / "wezterm" / "wezterm.lua"
    home_settings = Path.home() / HOME_SETTINGS_NAME
    state: WeztermState = {
        "installed": check_tool_exists(tool_name=WEZTERM_EXECUTABLE),
        "names": list(schemes_list),
        "path": str(path),
        "file": "missing",
        "current": None,
        "places": 0,
        "line": None,
        "detail": "",
        "shadow": str(home_settings) if home_settings.is_file() else "",
    }
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return state
    except (OSError, UnicodeDecodeError) as error:
        state["file"] = "unreadable"
        state["detail"] = str(error)
        return state
    names = [QUOTED_NAME.match(line) for line in lines if SCHEME_LINE.match(line) is not None]
    if len(names) > 0:
        held = {None if found is None else found.group(1) or found.group(2) for found in names}
        state["file"] = "ready"
        state["places"] = len(names)
        state["current"] = next(iter(held)) if len(held) == 1 else None
        return state
    switched_off = [number for number, line in enumerate(lines, start=1) if SWITCHED_OFF_LINE.match(line) is not None]
    state["file"] = "line_off" if len(switched_off) > 0 else "no_line"
    state["line"] = switched_off[0] if len(switched_off) > 0 else None
    return state


# The command's own function does the writing. A file it cannot write a theme into is turned down here in plain words, before it is tried.
def apply_scheme(body: object) -> WeztermState | WeztermProblem:
    from stackops.scripts.python.helpers.helpers_devops.themes.choose_wezterm_theme import schemes_list, set_theme

    name = cast(dict[str, object], body).get("name") if isinstance(body, dict) else None
    if not isinstance(name, str) or name not in schemes_list:
        return WeztermProblem(status=400, message=f"""{name} is not one of the themes this tool can apply.""")
    state = read_state()
    file_name = Path(state["path"]).name
    match state["file"]:
        case "missing":
            return WeztermProblem(status=409, message=f"""There is no {file_name} to save the theme in.""")
        case "unreadable":
            return WeztermProblem(status=409, message=f"""{file_name} could not be read: {state["detail"]}""")
        case "no_line":
            return WeztermProblem(status=409, message=f"""{file_name} has no line that sets the colour scheme.""")
        case "line_off":
            return WeztermProblem(status=409, message=f"""The line that sets the colour scheme is switched off in {file_name}.""")
        case "ready":
            pass
    try:
        set_theme(name)
    except (OSError, ValueError) as error:
        return WeztermProblem(status=409, message=str(error))
    return read_state()
