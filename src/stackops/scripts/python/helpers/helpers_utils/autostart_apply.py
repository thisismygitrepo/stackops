import platform
from dataclasses import dataclass
from pathlib import Path

from stackops.scripts.python.helpers.helpers_utils.autostart_entry import StartupEntryFailure
from stackops.scripts.python.helpers.helpers_utils.autostart_layout import add_startup_layout, remove_startup_layout
from stackops.scripts.python.helpers.helpers_utils.autostart_remembered import remembered_name_of
from stackops.scripts.python.helpers.helpers_utils.autostart_script import add_startup_script, remove_startup_script
from stackops.scripts.python.helpers.helpers_utils.autostart_script_entries import installed_startup_entries
from stackops.utils.schemas.startup.startup_constants import STARTUP_KINDS
from stackops.utils.schemas.startup.startup_file import read_startup_file
from stackops.utils.schemas.startup.startup_types import StartupEntryConfig, StartupKind
from stackops.utils.source_of_truth import DOTFILES_STARTUP_YAML_PATH, SCRIPTS_ROOT_PRIVATE


# What starts here out of the dotfiles without startup.yaml listing it: its kind, the name the file would list it by, and what its entry
# starts, a script's file or a layout's name.
@dataclass(frozen=True)
class UnlistedEntry:
    kind: StartupKind
    name: str
    target: str


# What startup.yaml lists for this system and is not started here, and what is started here out of the dotfiles without being listed.
@dataclass(frozen=True)
class StartupDrift:
    missing: tuple[StartupEntryConfig, ...]
    unlisted: tuple[UnlistedEntry, ...]


# Each of the three names what it is about the way a person would: a script by its file, a layout as "layout" and its name.
@dataclass(frozen=True)
class StartupApplied:
    added: tuple[str, ...]
    removed: tuple[str, ...]
    unlisted: tuple[str, ...]
    failures: tuple[StartupEntryFailure, ...]


# Without a startup.yaml there is no list to differ from, so nothing is missing and nothing is unlisted.
def read_startup_drift() -> StartupDrift:
    if not DOTFILES_STARTUP_YAML_PATH.is_file():
        return StartupDrift(missing=(), unlisted=())
    system = platform.system()
    listed: dict[tuple[StartupKind, str], StartupEntryConfig] = {(entry["kind"], entry["name"]): entry for entry in read_startup_file(path=DOTFILES_STARTUP_YAML_PATH)["entries"] if system.lower() in entry["os"]}
    started: dict[tuple[StartupKind, str], str] = {
        (kind, name): target
        for kind in STARTUP_KINDS
        for target in installed_startup_entries(kind=kind, system=system).values()
        if (name := remembered_name_of(kind=kind, target=target)) is not None
    }
    return StartupDrift(
        missing=tuple(entry for key, entry in listed.items() if key not in started),
        unlisted=tuple(UnlistedEntry(kind=kind, name=name, target=target) for (kind, name), target in started.items() if (kind, name) not in listed),
    )


# This machine is made to match startup.yaml: what the file lists for this system and is not started here is added. What starts here out
# of the dotfiles without being listed is stopped from starting when `prune` says so, and named otherwise: the file may have lost it, so
# taking it away is asked for. A script that is kept outside the dotfiles is never touched.
def apply_startup_file(search_path: str, prune: bool) -> StartupApplied:
    drift = read_startup_drift()
    added: list[str] = []
    removed: list[str] = []
    failures: list[StartupEntryFailure] = []
    unlisted = [(entry, Path(entry.target).name if entry.kind == "script" else f"""layout {entry.name}""") for entry in drift.unlisted]
    for entry, title in unlisted if prune else ():
        match entry.kind:
            case "script":
                gone = remove_startup_script(script_name=entry.target)
            case "layout":
                gone = remove_startup_layout(layout_name=entry.target)
        match gone:
            case StartupEntryFailure():
                failures.append(gone)
            case _:
                removed.append(title)
    for listed in drift.missing:
        match listed["kind"]:
            case "script":
                script_path = SCRIPTS_ROOT_PRIVATE / listed["name"]
                if not script_path.is_file() or remembered_name_of(kind="script", target=str(script_path)) != listed["name"]:
                    failures.append(StartupEntryFailure(reason="missing_script", message=f"""{DOTFILES_STARTUP_YAML_PATH.name} lists {listed["name"]}, which is not a script in {SCRIPTS_ROOT_PRIVATE}."""))
                    continue
                started = add_startup_script(script_path=script_path, search_path=search_path, when=listed["when"])
            case "layout":
                started = add_startup_layout(layout_name=listed["name"], search_path=search_path, when=listed["when"])
        match started:
            case StartupEntryFailure():
                failures.append(started)
            case _:
                added.append(listed["name"] if listed["kind"] == "script" else f"""layout {listed["name"]}""")
    return StartupApplied(added=tuple(added), removed=tuple(removed), unlisted=() if prune else tuple(title for _entry, title in unlisted), failures=tuple(failures))
