import platform
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from stackops.profile.dotfiles_constants import ALL_OS_VALUES, OsName
from stackops.scripts.python.helpers.helpers_utils.autostart_entry import StartupEntryAdded, StartupEntryFailure, StartupEntryRemoved
from stackops.scripts.python.helpers.helpers_utils.autostart_layout import add_startup_layout, remove_startup_layout
from stackops.scripts.python.helpers.helpers_utils.autostart_script import add_startup_script, remove_startup_script
from stackops.utils.schemas.startup.startup_constants import STARTUP_FILE_VERSION
from stackops.utils.schemas.startup.startup_file import read_startup_file, write_startup_file
from stackops.utils.schemas.startup.startup_types import StartupEntryConfig, StartupKind, StartupWhen
from stackops.utils.source_of_truth import DOTFILES_STARTUP_YAML_PATH, SCRIPTS_ROOT_PRIVATE


# `remembered_for` is the systems startup.yaml lists the entry for. It is empty for a script that is not in the dotfiles: that one starts
# on this machine only.
@dataclass(frozen=True)
class StartupEntryRemembered:
    added: StartupEntryAdded
    remembered_for: tuple[OsName, ...]


# The name startup.yaml knows what an entry starts by, or none when the dotfiles do not hold it. A script is known by its path inside the
# scripts folder of the dotfiles, the one place where a script is the same on every machine, and one kept anywhere else has no name. A
# layout is always one of the layout.yaml of the dotfiles, and is known by its own name.
def remembered_name_of(kind: StartupKind, target: str) -> str | None:
    match kind:
        case "layout":
            return target
        case "script":
            root = SCRIPTS_ROOT_PRIVATE.resolve()
            located = Path(target).parent.resolve() / Path(target).name
            return located.relative_to(root).as_posix() if located.is_relative_to(root) else None


# From now on startup.yaml lists the entry for `systems` with `when`, and with nothing else for those systems. Without a `when` it stops
# listing the entry for them. The file is only written when that changes it.
def list_entry(kind: StartupKind, name: str, systems: tuple[OsName, ...], when: StartupWhen | None) -> None:
    entries = read_startup_file(path=DOTFILES_STARTUP_YAML_PATH)["entries"] if DOTFILES_STARTUP_YAML_PATH.is_file() else []
    kept: list[StartupEntryConfig] = []
    for entry in entries:
        if entry["kind"] != kind or entry["name"] != name:
            kept.append(entry)
            continue
        others: list[OsName] = [system for system in entry["os"] if system not in systems]
        if entry["when"] == when:
            kept.append(StartupEntryConfig(kind=kind, name=name, os=[system for system in ALL_OS_VALUES if system in others or system in systems], when=entry["when"]))
        elif others:
            kept.append(StartupEntryConfig(kind=kind, name=name, os=others, when=entry["when"]))
    if when is not None and not any(entry["kind"] == kind and entry["name"] == name and entry["when"] == when for entry in kept):
        kept.append(StartupEntryConfig(kind=kind, name=name, os=[system for system in ALL_OS_VALUES if system in systems], when=when))
    if kept != entries:
        write_startup_file(path=DOTFILES_STARTUP_YAML_PATH, startup_file={"version": STARTUP_FILE_VERSION, "entries": kept})


# `target` is a script's file or a layout's name. It starts on this machine, and when the dotfiles hold it, it is listed in startup.yaml
# for this system and for `other_systems`, so `apply_startup_file` starts it on the other machines the dotfiles reach. What cannot hold
# on those machines is refused before anything is changed here, and so is a startup.yaml that cannot be read, which raises as
# `read_startup_file` does.
def add_and_remember(kind: StartupKind, target: str, search_path: str, when: StartupWhen, other_systems: tuple[OsName, ...]) -> StartupEntryRemembered | StartupEntryFailure:
    this = platform.system().lower()
    name = remembered_name_of(kind=kind, target=target)
    title = Path(target).name if kind == "script" else f"""Layout {target}"""
    elsewhere: tuple[OsName, ...] = tuple(system for system in ALL_OS_VALUES if system in other_systems and system != this)
    if name is None and elsewhere:
        return StartupEntryFailure(
            reason="cannot_remember",
            message=f"""{title} is not in {SCRIPTS_ROOT_PRIVATE}, so no other machine has it to start. It can start on this machine only.""",
        )
    beyond_linux = [system for system in elsewhere if system != "linux"]
    if when == "boot" and beyond_linux:
        return StartupEntryFailure(
            reason="boot_needs_administrator",
            message=f"""Starting with the computer can only be set up on Linux, so {title} cannot be listed for {", ".join(beyond_linux)} that way.""",
        )
    if name is not None and DOTFILES_STARTUP_YAML_PATH.is_file():
        read_startup_file(path=DOTFILES_STARTUP_YAML_PATH)
    match kind:
        case "script":
            added = add_startup_script(script_path=Path(target), search_path=search_path, when=when)
        case "layout":
            added = add_startup_layout(layout_name=target, search_path=search_path, when=when)
    match added:
        case StartupEntryFailure():
            return added
        case _:
            pass
    if name is None:
        return StartupEntryRemembered(added=added, remembered_for=())
    systems = (cast(OsName, this), *elsewhere)
    list_entry(kind=kind, name=name, systems=systems, when=when)
    return StartupEntryRemembered(added=added, remembered_for=systems)


# startup.yaml stops listing for this system what an entry started. For an entry that was taken away by other means than
# `remove_and_forget`. A script that is not one of the dotfiles was never listed.
def forget_entry(kind: StartupKind, target: str) -> None:
    name = remembered_name_of(kind=kind, target=target)
    if name is not None:
        list_entry(kind=kind, name=name, systems=(cast(OsName, platform.system().lower()),), when=None)


# `name` is the script as it was added, its file name or a path to it, or the layout's name. A startup.yaml that cannot be read stops
# this before the entry is touched, raising as `read_startup_file` does.
def remove_and_forget(kind: StartupKind, name: str) -> StartupEntryRemoved | StartupEntryFailure:
    if DOTFILES_STARTUP_YAML_PATH.is_file():
        read_startup_file(path=DOTFILES_STARTUP_YAML_PATH)
    match kind:
        case "script":
            removed = remove_startup_script(script_name=name)
        case "layout":
            removed = remove_startup_layout(layout_name=name)
    match removed:
        case StartupEntryFailure():
            return removed
        case _:
            forget_entry(kind=kind, target=removed.target)
            return removed
