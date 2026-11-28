import os
import plistlib
import shlex
from pathlib import Path
from typing import cast

from stackops.scripts.python.helpers.helpers_utils.autostart_script_constants import ENTRY_PREFIX, MACOS_LABEL_PREFIX


# Where the entry of the script called `slug` is kept: a launch agent of the account on macOS, a systemd unit of the account on Linux, and a
# file in the account's Startup folder on Windows. All three start when the person signs in, and `utils machine autostart` lists all three.
def entry_file_of(slug: str, system: str) -> Path | None:
    match system:
        case "Darwin":
            return Path.home() / "Library" / "LaunchAgents" / f"""{MACOS_LABEL_PREFIX}{slug}.plist"""
        case "Linux":
            return Path.home() / ".config" / "systemd" / "user" / f"""{ENTRY_PREFIX}{slug}.service"""
        case "Windows":
            return Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / f"""{ENTRY_PREFIX}{slug}.cmd"""
        case _:
            return None


# The script an entry runs: the last word of its command, read back out of the form `add_startup_script` wrote it in.
def script_of_entry(entry_file: Path, system: str) -> Path:
    match system:
        case "Darwin":
            return Path(cast(list[str], plistlib.loads(entry_file.read_bytes())["ProgramArguments"])[-1])
        case "Linux":
            command = next((line for line in entry_file.read_text(encoding="utf-8").splitlines() if line.startswith("ExecStart=")), None)
            if command is None:
                raise ValueError(f"""{entry_file} has no ExecStart line to read its script from.""")
            return Path(shlex.split(command.removeprefix("ExecStart="))[-1].replace("%%", "%").replace("$$", "$"))
        case _:
            command = entry_file.read_text(encoding="utf-8").splitlines()[-1].replace("%%", "%")
            return Path(shlex.split(command, posix=False)[-1].strip('"'))


# Every startup script StackOps has added for this account, by the file of its entry.
def installed_startup_scripts(system: str) -> dict[Path, Path]:
    pattern = entry_file_of(slug="*", system=system)
    if pattern is None or not pattern.parent.is_dir():
        return {}
    return {entry_file: script_of_entry(entry_file=entry_file, system=system) for entry_file in sorted(pattern.parent.glob(pattern.name))}
