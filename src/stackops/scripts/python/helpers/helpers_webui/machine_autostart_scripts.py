import os
import platform
from pathlib import Path
from typing import TypedDict

from stackops.profile.dotfiles_constants import OsName
from stackops.scripts.python.helpers.helpers_utils.autostart_apply import apply_startup_file, read_startup_drift
from stackops.scripts.python.helpers.helpers_utils.autostart_entry import StartupEntryFailure, StartupEntryFailureReason
from stackops.scripts.python.helpers.helpers_utils.autostart_remembered import add_and_remember, forget_entry
from stackops.scripts.python.helpers.helpers_utils.autostart_script_entries import installed_startup_entries
from stackops.scripts.python.helpers.helpers_webui.constants import LAUNCH_PATH_VARIABLE
from stackops.scripts.python.helpers.helpers_webui.machine_autostart_actions import remove_launch_agent
from stackops.scripts.python.helpers.helpers_webui.machine_autostart_model import ProblemReason, StartupProblem
from stackops.scripts.python.helpers.helpers_webui.scripts_files import ScriptProblem, read_scripts
from stackops.utils.schemas.layouts.layout_file import read_layouts_file
from stackops.utils.schemas.startup.startup_constants import STARTUP_KINDS
from stackops.utils.schemas.startup.startup_types import StartupKind, StartupWhen
from stackops.utils.source_of_truth import DOTFILES_LAYOUT_YAML_PATH, DOTFILES_STARTUP_YAML_PATH

PROBLEM_OF_FAILURE: dict[StartupEntryFailureReason, ProblemReason] = {
    "unsupported_system": "unsupported",
    "unsupported_kind": "refused",
    "already_added": "refused",
    "boot_needs_administrator": "refused",
    "cannot_remember": "refused",
    "not_added": "unknown_entry",
    "missing_layout": "unknown_entry",
    "missing_program": "failed",
    "missing_script": "failed",
    "system_refused": "failed",
}


# One of the layouts in the layout.yaml of the dotfiles, for picking the one to launch on its own.
class SavedLayout(TypedDict):
    name: str
    tabs: int
    panes: int


class SavedLayouts(TypedDict):
    file: str
    layouts: list[SavedLayout]


class ListedEntry(TypedDict):
    kind: StartupKind
    name: str
    when: StartupWhen


class UnlistedView(TypedDict):
    kind: StartupKind
    name: str


# How this machine differs from startup.yaml: what the file lists for this system and is not started here, and what starts here out of
# the dotfiles without being listed. A script is named by its file, a layout by its own name.
class RememberedView(TypedDict):
    file: str
    missing: list[ListedEntry]
    unlisted: list[UnlistedView]


class AppliedView(TypedDict):
    added: list[str]
    removed: list[str]
    failures: list[str]


def _added(kind: StartupKind, target: str, when: StartupWhen, other_systems: tuple[OsName, ...]) -> StartupProblem | None:
    try:
        result = add_and_remember(kind=kind, target=target, search_path=os.environ[LAUNCH_PATH_VARIABLE], when=when, other_systems=other_systems)
    except ValueError as error:
        return StartupProblem(reason="failed", message=str(error))
    match result:
        case StartupEntryFailure():
            return StartupProblem(reason=PROBLEM_OF_FAILURE[result.reason], message=result.message)
        case _:
            return None


# Adding is what `utils machine autostart-add` does, through the command's own helper. The script is looked up in a fresh read of the places
# the Scripts page lists from `base_directory`, so the page can name nothing but a script StackOps keeps, whatever it sends. The script is
# given the PATH the web UI was started with, not this server's own, which uv has put its own folders in front of.
def add_tracked_script(base_directory: str, script_path: str, when: StartupWhen, other_systems: tuple[OsName, ...]) -> StartupProblem | None:
    listed = read_scripts(base_directory=base_directory)
    match listed:
        case ScriptProblem():
            return StartupProblem(reason="refused", message=listed.message)
        case _:
            tracked = any(script["path"] == script_path for place in listed["places"] for script in place["scripts"])
    if not tracked:
        return StartupProblem(reason="unknown_entry", message="That script is no longer among the ones StackOps keeps. It may have been renamed or removed.")
    return _added(kind="script", target=script_path, when=when, other_systems=other_systems)


# What `utils machine autostart-add --kind layout` does. The layout is looked up afresh in the layout.yaml of the dotfiles by the helper.
def add_saved_layout(layout_name: str, when: StartupWhen, other_systems: tuple[OsName, ...]) -> StartupProblem | None:
    return _added(kind="layout", target=layout_name, when=when, other_systems=other_systems)


def read_saved_layouts() -> SavedLayouts | StartupProblem:
    try:
        layouts = read_layouts_file(path=DOTFILES_LAYOUT_YAML_PATH)["layouts"] if DOTFILES_LAYOUT_YAML_PATH.is_file() else []
    except ValueError as error:
        return StartupProblem(reason="failed", message=str(error))
    return SavedLayouts(
        file=str(DOTFILES_LAYOUT_YAML_PATH),
        layouts=[SavedLayout(name=layout["layoutName"], tabs=len(layout["layoutTabs"]), panes=sum(len(tab["panes"]) for tab in layout["layoutTabs"])) for layout in layouts],
    )


# A launch agent moved to the Trash from the page. When it is one that started a script or a layout, startup.yaml stops listing that for
# this system, as `utils machine autostart-remove` has it: otherwise the page would go on saying it is not started here yet.
def remove_startup_agent(identifier: str) -> StartupProblem | None:
    entry_file = Path(identifier.removeprefix("launchd:"))
    started: tuple[StartupKind, str] | None = next(
        ((kind, target) for kind in STARTUP_KINDS if (target := installed_startup_entries(kind=kind, system=platform.system()).get(entry_file)) is not None), None,
    )
    problem = remove_launch_agent(identifier)
    if problem is not None or started is None:
        return problem
    try:
        forget_entry(kind=started[0], target=started[1])
    except ValueError as error:
        return StartupProblem(reason="failed", message=f"""It no longer starts here, but startup.yaml still lists it: {error}""")
    return None


def read_remembered() -> RememberedView | StartupProblem:
    try:
        drift = read_startup_drift()
    except ValueError as error:
        return StartupProblem(reason="failed", message=str(error))
    return RememberedView(
        file=str(DOTFILES_STARTUP_YAML_PATH),
        missing=[ListedEntry(kind=entry["kind"], name=entry["name"], when=entry["when"]) for entry in drift.missing],
        unlisted=[UnlistedView(kind=entry.kind, name=Path(entry.target).name if entry.kind == "script" else entry.name) for entry in drift.unlisted],
    )


# What `utils machine autostart-apply` does, through the command's own helper, with the PATH the web UI was started with.
def apply_remembered(prune: bool) -> AppliedView | StartupProblem:
    try:
        applied = apply_startup_file(search_path=os.environ[LAUNCH_PATH_VARIABLE], prune=prune)
    except ValueError as error:
        return StartupProblem(reason="failed", message=str(error))
    return AppliedView(added=list(applied.added), removed=list(applied.removed), failures=[failure.message for failure in applied.failures])
