import platform
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from stackops.profile.dotfiles_constants import ALL_OS_VALUES, OsName
from stackops.scripts.python.helpers.helpers_utils.autostart_script import (
    StartupScriptAdded,
    StartupScriptFailure,
    StartupScriptRemoved,
    add_startup_script,
    remove_startup_script,
)
from stackops.scripts.python.helpers.helpers_utils.autostart_script_entries import installed_startup_scripts
from stackops.utils.schemas.startup.startup_constants import STARTUP_FILE_VERSION
from stackops.utils.schemas.startup.startup_file import read_startup_file, write_startup_file
from stackops.utils.schemas.startup.startup_types import StartupEntryConfig, StartupWhen
from stackops.utils.source_of_truth import DOTFILES_STARTUP_YAML_PATH, SCRIPTS_ROOT_PRIVATE


# `remembered_for` is the systems startup.yaml lists the script for. It is empty for a script that is not in the dotfiles: that one starts
# on this machine only.
@dataclass(frozen=True)
class StartupScriptRemembered:
    added: StartupScriptAdded
    remembered_for: tuple[OsName, ...]


# What startup.yaml lists for this system and is not started here, and the scripts of the dotfiles that are started here without being listed.
@dataclass(frozen=True)
class StartupDrift:
    missing: tuple[StartupEntryConfig, ...]
    unlisted: tuple[Path, ...]


@dataclass(frozen=True)
class StartupApplied:
    added: tuple[str, ...]
    removed: tuple[str, ...]
    unlisted: tuple[str, ...]
    failures: tuple[StartupScriptFailure, ...]


# The name startup.yaml knows a script by: its path inside the scripts folder of the dotfiles, the one place where a script is the same on
# every machine. A script kept anywhere else has none.
def remembered_name_of(script_path: Path) -> str | None:
    root = SCRIPTS_ROOT_PRIVATE.resolve()
    located = script_path.parent.resolve() / script_path.name
    return located.relative_to(root).as_posix() if located.is_relative_to(root) else None


# From now on startup.yaml lists the script for `systems` with `when`, and with nothing else for those systems. Without a `when` it stops
# listing the script for them. The file is only written when that changes it.
def list_script(name: str, systems: tuple[OsName, ...], when: StartupWhen | None) -> None:
    entries = read_startup_file(path=DOTFILES_STARTUP_YAML_PATH)["entries"] if DOTFILES_STARTUP_YAML_PATH.is_file() else []
    kept: list[StartupEntryConfig] = []
    for entry in entries:
        if entry["kind"] != "script" or entry["name"] != name:
            kept.append(entry)
            continue
        others: list[OsName] = [system for system in entry["os"] if system not in systems]
        if entry["when"] == when:
            kept.append(StartupEntryConfig(kind="script", name=name, os=[system for system in ALL_OS_VALUES if system in others or system in systems], when=entry["when"]))
        elif others:
            kept.append(StartupEntryConfig(kind="script", name=name, os=others, when=entry["when"]))
    if when is not None and not any(entry["kind"] == "script" and entry["name"] == name and entry["when"] == when for entry in kept):
        kept.append(StartupEntryConfig(kind="script", name=name, os=[system for system in ALL_OS_VALUES if system in systems], when=when))
    if kept != entries:
        write_startup_file(path=DOTFILES_STARTUP_YAML_PATH, startup_file={"version": STARTUP_FILE_VERSION, "entries": kept})


# The script starts on this machine, and when it is one of the dotfiles it is listed in startup.yaml for this system and for
# `other_systems`, so `apply_startup_file` starts it on the other machines the dotfiles reach. What cannot hold on those machines is
# refused before anything is changed here, and so is a startup.yaml that cannot be read, which raises as `read_startup_file` does.
def add_and_remember(script_path: Path, search_path: str, when: StartupWhen, other_systems: tuple[OsName, ...]) -> StartupScriptRemembered | StartupScriptFailure:
    this = platform.system().lower()
    name = remembered_name_of(script_path)
    elsewhere: tuple[OsName, ...] = tuple(system for system in ALL_OS_VALUES if system in other_systems and system != this)
    if name is None and elsewhere:
        return StartupScriptFailure(
            reason="cannot_remember",
            message=f"""{script_path.name} is not in {SCRIPTS_ROOT_PRIVATE}, so no other machine has it to start. It can start on this machine only.""",
        )
    beyond_linux = [system for system in elsewhere if system != "linux"]
    if when == "boot" and beyond_linux:
        return StartupScriptFailure(
            reason="boot_needs_administrator",
            message=f"""Starting with the computer can only be set up on Linux, so {script_path.name} cannot be listed for {", ".join(beyond_linux)} that way.""",
        )
    if name is not None and DOTFILES_STARTUP_YAML_PATH.is_file():
        read_startup_file(path=DOTFILES_STARTUP_YAML_PATH)
    added = add_startup_script(script_path=script_path, search_path=search_path, when=when)
    match added:
        case StartupScriptFailure():
            return added
        case _:
            pass
    if name is None:
        return StartupScriptRemembered(added=added, remembered_for=())
    systems = (cast(OsName, this), *elsewhere)
    list_script(name=name, systems=systems, when=when)
    return StartupScriptRemembered(added=added, remembered_for=systems)


# startup.yaml stops listing the script for this system. For a script that was removed from what starts here by other means than
# `remove_and_forget`, and a script that is not one of the dotfiles was never listed.
def forget_script(script_path: Path) -> None:
    name = remembered_name_of(script_path)
    if name is not None:
        list_script(name=name, systems=(cast(OsName, platform.system().lower()),), when=None)


# A startup.yaml that cannot be read stops this before the entry is touched, raising as `read_startup_file` does.
def remove_and_forget(script_name: str) -> StartupScriptRemoved | StartupScriptFailure:
    if DOTFILES_STARTUP_YAML_PATH.is_file():
        read_startup_file(path=DOTFILES_STARTUP_YAML_PATH)
    removed = remove_startup_script(script_name=script_name)
    match removed:
        case StartupScriptFailure():
            return removed
        case _:
            forget_script(script_path=removed.script_path)
            return removed


# Without a startup.yaml there is no list to differ from, so nothing is missing and nothing is unlisted.
def read_startup_drift() -> StartupDrift:
    if not DOTFILES_STARTUP_YAML_PATH.is_file():
        return StartupDrift(missing=(), unlisted=())
    system = platform.system()
    listed = {entry["name"]: entry for entry in read_startup_file(path=DOTFILES_STARTUP_YAML_PATH)["entries"] if entry["kind"] == "script" and system.lower() in entry["os"]}
    started = {name: script for script in installed_startup_scripts(system=system).values() if (name := remembered_name_of(script)) is not None}
    return StartupDrift(
        missing=tuple(entry for name, entry in listed.items() if name not in started),
        unlisted=tuple(script for name, script in started.items() if name not in listed),
    )


# This machine is made to match startup.yaml: what the file lists for this system and is not started here is added. The scripts of the
# dotfiles that start here without being listed are stopped from starting when `prune` says so, and named otherwise: the file may have
# lost them, so taking them away is asked for. A script that is kept outside the dotfiles is never touched.
def apply_startup_file(search_path: str, prune: bool) -> StartupApplied:
    drift = read_startup_drift()
    added: list[str] = []
    removed: list[str] = []
    failures: list[StartupScriptFailure] = []
    for script in drift.unlisted if prune else ():
        gone = remove_startup_script(script_name=str(script))
        match gone:
            case StartupScriptFailure():
                failures.append(gone)
            case _:
                removed.append(script.name)
    for entry in drift.missing:
        script_path = SCRIPTS_ROOT_PRIVATE / entry["name"]
        if not script_path.is_file() or remembered_name_of(script_path) != entry["name"]:
            failures.append(StartupScriptFailure(reason="missing_script", message=f"""{DOTFILES_STARTUP_YAML_PATH.name} lists {entry["name"]}, which is not a script in {SCRIPTS_ROOT_PRIVATE}."""))
            continue
        started = add_startup_script(script_path=script_path, search_path=search_path, when=entry["when"])
        match started:
            case StartupScriptFailure():
                failures.append(started)
            case _:
                added.append(entry["name"])
    return StartupApplied(added=tuple(added), removed=tuple(removed), unlisted=() if prune else tuple(script.name for script in drift.unlisted), failures=tuple(failures))
