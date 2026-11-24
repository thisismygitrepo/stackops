import shlex
from typing import TypedDict

from stackops.scripts.python.helpers.helpers_webui.terminal_shell_profile_constants import (
    ALIAS_WRAPPER,
    NUSHELL_ALIAS,
    PWSH_ALIAS,
    PWSH_FUNCTION,
    PWSH_NOISE,
    SHELL_EXTRAS,
    ShellFamily,
)
from stackops.utils.cli_utils.command_lookup import check_tool_exists


# A short name the setup gives a command: typing `name` runs `runs`.
class ShellAlias(TypedDict):
    name: str
    runs: str


class ExtraProgram(TypedDict):
    name: str
    installed: bool


# One part of the setup, such as the prompt, with the programs it can use in the order the script tries them. A part that needs none has an empty list.
class ShellExtra(TypedDict):
    key: str
    programs: list[ExtraProgram]


class ShellGives(TypedDict):
    aliases: list[ShellAlias]
    extras: list[ShellExtra]


# Not a shell parser: only one-line definitions with a fixed name are read, which is how the setup scripts write them. A name built in a loop is left out.
def _posix_aliases(lines: list[str]) -> list[ShellAlias]:
    aliases: list[ShellAlias] = []
    for line in lines:
        if not line.startswith("alias "):
            continue
        try:
            words = shlex.split(line.removeprefix("alias "), comments=True)
        except ValueError:
            continue
        for word in words:
            name, separator, runs = word.partition("=")
            if separator == "=" and "$" not in word:
                aliases.append({"name": name, "runs": runs.removeprefix(ALIAS_WRAPPER)})
    return aliases


def _nushell_aliases(lines: list[str]) -> list[ShellAlias]:
    matches = [NUSHELL_ALIAS.fullmatch(line) for line in lines]
    return [{"name": found["name"], "runs": found["runs"].removeprefix(ALIAS_WRAPPER)} for found in matches if found is not None]


# PowerShell gives a short name either as a one-line function or as an alias of one. A function that only wraps the command of its own name is no
# short name, and one that an alias points at is shown under the alias.
def _pwsh_aliases(lines: list[str]) -> list[ShellAlias]:
    functions: dict[str, str] = {}
    renames: dict[str, str] = {}
    for line in lines:
        function = PWSH_FUNCTION.fullmatch(line)
        if function is not None:
            functions.setdefault(function["name"], PWSH_NOISE.sub("", function["runs"].removeprefix(ALIAS_WRAPPER)).strip())
        rename = PWSH_ALIAS.match(line)
        if rename is not None:
            renames.setdefault(rename["name"], rename["runs"])
    renamed = {name: functions[target] for name, target in renames.items() if target in functions}
    direct = {name: runs for name, runs in functions.items() if name != runs and name not in renames.values()}
    return [{"name": name, "runs": runs} for name, runs in {**direct, **renamed}.items()]


# What a setup script gives a terminal, read from its text: the short commands it defines, and which of the known parts it switches on.
def read_shell_gives(family: ShellFamily, text: str) -> ShellGives:
    lines = [line.strip() for line in text.splitlines() if not line.lstrip().startswith("#")]
    match family:
        case "posix":
            aliases = _posix_aliases(lines)
        case "nushell":
            aliases = _nushell_aliases(lines)
        case "pwsh":
            aliases = _pwsh_aliases(lines)
    code = "\n".join(lines)
    found: dict[str, list[tuple[int, str]]] = {}
    for key, program, pattern in SHELL_EXTRAS:
        place = pattern.search(code)
        if place is not None:
            found.setdefault(key, []).append((place.start(), program))
    extras: list[ShellExtra] = [
        {"key": key, "programs": [{"name": program, "installed": check_tool_exists(tool_name=program)} for _, program in sorted(places) if program != ""]}
        for key, places in found.items()
    ]
    return {"aliases": aliases, "extras": extras}
