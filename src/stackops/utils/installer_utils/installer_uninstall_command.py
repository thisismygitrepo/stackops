import platform
import re
import shlex
import subprocess
from typing import Final


_SEGMENT_SEPARATORS: Final[frozenset[str]] = frozenset({"&&", ";"})
_OPTIONS_TAKING_A_VALUE: Final[frozenset[str]] = frozenset({"--python", "-p", "--with", "--from", "--source", "--scope", "--name", "--installer-type"})
_VERSION_OR_EXTRAS_SUFFIX: Final[re.Pattern[str]] = re.compile(r"(?!^)@|[\[=<>!~]")


# Design choice: only an install command that is understood whole gets an uninstall command. That is one install of one package, with nothing
# around it but a refresh of the package lists. A longer command also installs things the app merely needs, or sets up files, and which package
# is the app itself cannot be told from the text, so it gets none. The system package managers get no "yes to all" switch: removing a package
# can take others with it, and their own question shows which.
def derive_uninstall_command(install_command: str) -> str | None:
    lexer = shlex.shlex(install_command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    try:
        tokens = list(lexer)
    except ValueError:
        return None
    segments: list[list[str]] = [[]]
    for token in tokens:
        if token in _SEGMENT_SEPARATORS:
            segments.append([])
        else:
            segments[-1].append(token)
    removals: list[list[str]] = []
    for segment in segments:
        privilege = segment[:1] if segment[:1] == ["sudo"] else []
        package_has_version = False
        match segment[len(privilege) :]:
            case [] | ["apt-get" | "apt" | "nala" | "brew", "update"] | ["brew", "tap", _]:
                continue
            case ["apt-get" | "apt" | "nala" | "dnf" as manager, "install", *arguments]:
                removal = [*privilege, manager, "remove"]
            case ["pacman", "-S", *arguments]:
                removal = [*privilege, "pacman", "-R"]
            case ["apk", "add", *arguments]:
                removal = [*privilege, "apk", "del"]
            case ["brew", "install", *arguments]:
                removal = ["brew", "uninstall", "--cask"] if "--cask" in arguments else ["brew", "uninstall"]
            case ["bun", "install" | "add" | "i", *arguments] if "-g" in arguments or "--global" in arguments:
                removal, package_has_version = ["bun", "remove", "-g"], True
            case ["npm", "install" | "i", *arguments] if "-g" in arguments or "--global" in arguments:
                removal, package_has_version = ["npm", "uninstall", "-g"], True
            case ["cargo", "install", *arguments]:
                removal, package_has_version = ["cargo", "uninstall"], True
            case ["uv", "tool", "install", *arguments]:
                removal, package_has_version = ["uv", "tool", "uninstall"], True
            case ["winget", "install", *arguments]:
                removal = ["winget", "uninstall", "--exact", "--id"] if any(argument.lower() == "--id" for argument in arguments) else ["winget", "uninstall"]
            case _:
                return None
        remaining = iter(arguments)
        packages: list[str] = []
        for argument in remaining:
            if argument in _OPTIONS_TAKING_A_VALUE:
                next(remaining, None)
            elif not argument.startswith("-"):
                packages.append(argument)
        if len(packages) != 1 or packages[0].startswith((".", "/")) or "://" in packages[0]:
            return None
        removals.append([*removal, _VERSION_OR_EXTRAS_SUFFIX.split(packages[0], maxsplit=1)[0] if package_has_version else packages[0]])
    if len(removals) != 1:
        return None
    return subprocess.list2cmdline(removals[0]) if platform.system() == "Windows" else shlex.join(removals[0])
