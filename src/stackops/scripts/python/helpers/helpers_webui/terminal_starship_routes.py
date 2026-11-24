import os
import shutil
import subprocess
from pathlib import Path
from typing import Literal, TypedDict

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from stackops.scripts.python.helpers.helpers_webui.terminal_starship_constants import (
    STARSHIP_ANSWER_TIMEOUT_SECONDS,
    STARSHIP_PICKER_TOOLS,
    STARSHIP_SETTINGS_FILE_NAME,
)

# What the settings file holds: nothing (Starship then draws its standard prompt), one of Starship's presets exactly as Starship writes it out,
# settings of the person's own, or something that could not be read.
type StarshipSettingsKind = Literal["standard", "preset", "own", "unreadable"]


# What the Starship sheet shows before anything is chosen. `settings_path` is the file Starship reads. The command can write another one: picking
# by name follows XDG_CONFIG_HOME, which Starship ignores, and the picker always writes the file in the home folder, whatever STARSHIP_CONFIG says.
# `by_name_elsewhere` and `picker_elsewhere` hold that other file, and are empty when the write lands in the file Starship reads.
# `picker_tool` is the program the picker shows its list with, empty when none is installed. Only `installed` is filled in when Starship is missing.
class StarshipState(TypedDict):
    installed: bool
    version: str
    settings_path: str
    kind: StarshipSettingsKind
    preset: str
    problem: str
    by_name_elsewhere: str
    picker_elsewhere: str
    picker_tool: str


def read_starship_state() -> StarshipState:
    home_settings = Path.home() / ".config" / STARSHIP_SETTINGS_FILE_NAME
    settings = Path(os.environ.get("STARSHIP_CONFIG", str(home_settings))).expanduser()
    # The file `configure_named_theme` writes for a preset's name.
    by_name = Path(os.environ.get("STARSHIP_CONFIG", str(Path(os.environ.get("XDG_CONFIG_HOME", "~/.config")).expanduser() / STARSHIP_SETTINGS_FILE_NAME))).expanduser()
    state: StarshipState = {
        "installed": False, "version": "", "settings_path": str(settings), "kind": "standard", "preset": "", "problem": "",
        "by_name_elsewhere": "" if by_name.resolve() == settings.resolve() else str(by_name),
        "picker_elsewhere": "" if home_settings.resolve() == settings.resolve() else str(home_settings),
        "picker_tool": next((tool for tool in STARSHIP_PICKER_TOOLS if shutil.which(tool) is not None), ""),
    }
    starship = shutil.which("starship")
    if starship is None:
        return state

    def ask(*arguments: str) -> str:
        return subprocess.run([starship, *arguments], check=True, capture_output=True, encoding="utf-8", timeout=STARSHIP_ANSWER_TIMEOUT_SECONDS).stdout

    state["installed"] = True
    state["version"] = ask("--version").split("\n")[0].removeprefix("starship").strip()
    try:
        text = settings.read_text(encoding="utf-8") if settings.is_file() else ""
    except (OSError, UnicodeDecodeError) as error:
        return {**state, "kind": "unreadable", "problem": str(error)}
    if text.strip() == "":
        return state
    # The comparison stays on this side: the page is told which preset the file equals, never what the file says.
    in_use = next((name for name in dict.fromkeys(line.strip() for line in ask("preset", "--list").splitlines()) if name != "" and ask("preset", name) == text), "")
    return {**state, "kind": "preset" if in_use != "" else "own", "preset": in_use}


def terminal_starship_routes() -> list[Route]:
    def read_state(_request: Request) -> JSONResponse:
        try:
            return JSONResponse(read_starship_state())
        except (OSError, subprocess.SubprocessError) as error:
            return JSONResponse({"error": f"""Starship is installed but did not answer: {error}"""}, status_code=502)

    return [Route("/api/terminal/starship/state", read_state)]
