import os
import re
import sys
import time
from pathlib import Path

from stackops.scripts.python.helpers.helpers_utils.autostart_common import categorize
from stackops.scripts.python.helpers.helpers_webui.machine_autostart_constants import (
    GONE_MESSAGE,
    LOCKED_MESSAGE,
    RUN_KEY_SOURCE,
    STARTUP_APPROVED_OFF_MARKS,
    STARTUP_APPROVED_OFF_START,
    STARTUP_APPROVED_ON,
    STARTUP_FOLDER_SOURCE,
    WINDOWS_CLOCK_OFFSET_SECONDS,
    WINDOWS_VERSION_KEY,
)
from stackops.scripts.python.helpers.helpers_webui.machine_autostart_model import EntryAction, StartupEntry, StartupProblem

RUN_KEY = f"""{WINDOWS_VERSION_KEY}\\Run"""
APPROVED_KEY = f"""{WINDOWS_VERSION_KEY}\\Explorer\\StartupApproved"""
# The program a Run value starts: what is in quotes, else everything up to the first .exe, else the first word.
PROGRAM_OF_COMMAND = re.compile(r"""^\s*"([^"]+)"|^\s*(.+?\.exe)\b|^\s*(\S+)""", re.IGNORECASE)


# The values of one key of the person's own part of the registry, as (name, data, kind). Nothing when the key is not there.
def _values(key_path: str) -> list[tuple[str, object, int]]:
    if sys.platform != "win32":
        raise RuntimeError("The registry is only there on Windows.")
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
            return [winreg.EnumValue(key, index) for index in range(winreg.QueryInfoKey(key)[1])]
    except FileNotFoundError:
        return []


# The names Windows was told to pass over at sign-in, in the list Task Manager keeps under `kind`.
def _turned_off(kind: str) -> set[str]:
    return {name for name, data, _kind in _values(f"""{APPROVED_KEY}\\{kind}""") if isinstance(data, bytes) and data[:1] and data[0] in STARTUP_APPROVED_OFF_MARKS}


def _entry(identifier: str, name: str, description: str, source: str, program: str, file: str, enabled: bool) -> StartupEntry:
    return StartupEntry(
        id=identifier,
        kind="sign_in",
        name=name,
        title=name,
        description=description,
        category=categorize(name, fallback="apps-services"),
        scope="login",
        source=source,
        stock=False,
        whose="yours",
        owner="",
        enabled=enabled,
        manner="always",
        triggers=[],
        program=program,
        file=file,
        live="unknown",
        pid=None,
        last_exit=None,
        actions=["turn_off"] if enabled else ["turn_on"],
        lock="",
    )


# What Windows opens at sign-in for the person alone: the values of their Run key and the files in their Startup folder, named as the command
# names them. The command leaves out the ones that are turned off; they are kept here, so they can be turned back on.
def read_windows_own_entries() -> list[StartupEntry]:
    if sys.platform != "win32":
        raise RuntimeError("The registry is only there on Windows.")
    import winreg

    entries: list[StartupEntry] = []
    run_off = _turned_off("Run")
    for name, data, kind in _values(RUN_KEY):
        if kind not in (winreg.REG_SZ, winreg.REG_EXPAND_SZ):
            continue
        program = PROGRAM_OF_COMMAND.match(winreg.ExpandEnvironmentStrings(str(data)))
        entries.append(
            _entry(
                identifier=f"""run:{name}""", name=name or "(Default)", description="Runs at login", source=RUN_KEY_SOURCE,
                program=next((part for part in program.groups() if part), "") if program is not None else "", file="", enabled=name not in run_off,
            )
        )
    folder = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    folder_off = _turned_off("StartupFolder")
    for item in sorted(folder.iterdir()) if folder.is_dir() else []:
        if item.is_file() and item.name != "desktop.ini":
            entries.append(
                _entry(
                    identifier=f"""startup:{item.name}""", name=item.stem, description=item.name, source=STARTUP_FOLDER_SOURCE,
                    program="", file=str(item), enabled=item.name not in folder_off,
                )
            )
    return entries


# The switch is the one Task Manager flips under Startup apps, so both show the same. What is asked for is looked up in a fresh read first
# and only done when that read offers it. Whatever is open now stays open: Windows only reads the switch at sign-in.
def switch_windows_entry(identifier: str, on: bool) -> StartupProblem | None:
    if sys.platform != "win32":
        raise RuntimeError("The registry is only there on Windows.")
    import winreg

    action: EntryAction = "turn_on" if on else "turn_off"
    entry = next((candidate for candidate in read_windows_own_entries() if candidate["id"] == identifier), None)
    if entry is None:
        return StartupProblem(reason="unknown_entry", message=GONE_MESSAGE)
    if action not in entry["actions"]:
        return StartupProblem(reason="refused", message=f"""{entry["title"]}: {LOCKED_MESSAGE}""")
    kind, _, name = identifier.partition(":")
    if on:
        approval = STARTUP_APPROVED_ON
    else:
        approval = STARTUP_APPROVED_OFF_START + int((time.time() + WINDOWS_CLOCK_OFFSET_SECONDS) * 10_000_000).to_bytes(8, "little")
    try:
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, f"""{APPROVED_KEY}\\{"Run" if kind == "run" else "StartupFolder"}""", 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as key:
            winreg.SetValueEx(key, name, 0, winreg.REG_BINARY, approval)
    except OSError as error:
        return StartupProblem(reason="failed", message=f"""Windows could not turn {entry["title"]} {"back on" if on else "off"}: {error}""")
    return None
