import os
import plistlib
import shlex
from pathlib import Path
from typing import cast

from stackops.scripts.python.helpers.helpers_utils.autostart_script_constants import ENTRY_PREFIX, LAYOUT_ENTRY_PREFIX, MACOS_LABEL_PREFIX, MACOS_LAYOUT_LABEL_PREFIX
from stackops.utils.schemas.startup.startup_types import StartupKind

ENTRY_PREFIXES: dict[StartupKind, str] = {"script": ENTRY_PREFIX, "layout": LAYOUT_ENTRY_PREFIX}
MACOS_LABEL_PREFIXES: dict[StartupKind, str] = {"script": MACOS_LABEL_PREFIX, "layout": MACOS_LAYOUT_LABEL_PREFIX}


# Where the entry of the script or layout called `slug` is kept: a launch agent of the account on macOS, a systemd unit of the account on
# Linux, and a file in the account's Startup folder on Windows. All three start when the person signs in, and `utils machine autostart`
# lists all three.
def entry_file_of(kind: StartupKind, slug: str, system: str) -> Path | None:
    match system:
        case "Darwin":
            return Path.home() / "Library" / "LaunchAgents" / f"""{MACOS_LABEL_PREFIXES[kind]}{slug}.plist"""
        case "Linux":
            return Path.home() / ".config" / "systemd" / "user" / f"""{ENTRY_PREFIXES[kind]}{slug}.service"""
        case "Windows":
            return Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / f"""{ENTRY_PREFIXES[kind]}{slug}.cmd"""
        case _:
            return None


# What an entry starts: the last word of its command, read back out of the form `add_startup_entry` wrote it in. For a script that is its
# file, for a layout its name.
def target_of_entry(entry_file: Path, system: str) -> str:
    match system:
        case "Darwin":
            return cast(list[str], plistlib.loads(entry_file.read_bytes())["ProgramArguments"])[-1]
        case "Linux":
            command = next((line for line in entry_file.read_text(encoding="utf-8").splitlines() if line.startswith("ExecStart=")), None)
            if command is None:
                raise ValueError(f"""{entry_file} has no ExecStart line to read what it starts from.""")
            return shlex.split(command.removeprefix("ExecStart="))[-1].replace("%%", "%").replace("$$", "$")
        case _:
            command = entry_file.read_text(encoding="utf-8").splitlines()[-1].replace("%%", "%")
            return shlex.split(command, posix=False)[-1].strip('"')


# Every script, or every layout, StackOps has set to start on its own for this account: what each starts, by the file of its entry.
def installed_startup_entries(kind: StartupKind, system: str) -> dict[Path, str]:
    pattern = entry_file_of(kind=kind, slug="*", system=system)
    if pattern is None or not pattern.parent.is_dir():
        return {}
    return {entry_file: target_of_entry(entry_file=entry_file, system=system) for entry_file in sorted(pattern.parent.glob(pattern.name))}
