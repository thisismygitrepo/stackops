import os
import platform
from pathlib import Path
from typing import TypedDict

from stackops.profile.dotfiles_constants import OsName
from stackops.scripts.python.helpers.helpers_utils.autostart_remembered import add_and_remember, apply_startup_file, forget_script, read_startup_drift
from stackops.scripts.python.helpers.helpers_utils.autostart_script import StartupScriptFailure, StartupScriptFailureReason
from stackops.scripts.python.helpers.helpers_utils.autostart_script_entries import installed_startup_scripts
from stackops.scripts.python.helpers.helpers_webui.constants import LAUNCH_PATH_VARIABLE
from stackops.scripts.python.helpers.helpers_webui.machine_autostart_actions import remove_launch_agent
from stackops.scripts.python.helpers.helpers_webui.machine_autostart_model import ProblemReason, StartupProblem
from stackops.scripts.python.helpers.helpers_webui.scripts_files import ScriptProblem, read_scripts
from stackops.utils.schemas.startup.startup_types import StartupWhen
from stackops.utils.source_of_truth import DOTFILES_STARTUP_YAML_PATH

PROBLEM_OF_FAILURE: dict[StartupScriptFailureReason, ProblemReason] = {
    "unsupported_system": "unsupported",
    "unsupported_kind": "refused",
    "already_added": "refused",
    "boot_needs_administrator": "refused",
    "cannot_remember": "refused",
    "not_added": "unknown_entry",
    "missing_program": "failed",
    "missing_script": "failed",
    "system_refused": "failed",
}


class ListedScript(TypedDict):
    name: str
    when: StartupWhen


# How this machine differs from startup.yaml: what the file lists for this system and is not started here, and the scripts of the
# dotfiles that start here without being listed.
class RememberedView(TypedDict):
    file: str
    missing: list[ListedScript]
    unlisted: list[str]


class AppliedView(TypedDict):
    added: list[str]
    removed: list[str]
    failures: list[str]


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
    try:
        result = add_and_remember(script_path=Path(script_path), search_path=os.environ[LAUNCH_PATH_VARIABLE], when=when, other_systems=other_systems)
    except ValueError as error:
        return StartupProblem(reason="failed", message=str(error))
    match result:
        case StartupScriptFailure():
            return StartupProblem(reason=PROBLEM_OF_FAILURE[result.reason], message=result.message)
        case _:
            return None


# A launch agent moved to the Trash from the page. When it is one that started a script, startup.yaml stops listing that script for this
# system, as `utils machine autostart-remove` has it: otherwise the page would go on saying the script is not started here yet.
def remove_startup_agent(identifier: str) -> StartupProblem | None:
    script = installed_startup_scripts(system=platform.system()).get(Path(identifier.removeprefix("launchd:")))
    problem = remove_launch_agent(identifier)
    if problem is not None or script is None:
        return problem
    try:
        forget_script(script_path=script)
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
        missing=[ListedScript(name=entry["name"], when=entry["when"]) for entry in drift.missing],
        unlisted=[script.name for script in drift.unlisted],
    )


# What `utils machine autostart-apply` does, through the command's own helper, with the PATH the web UI was started with.
def apply_remembered(prune: bool) -> AppliedView | StartupProblem:
    try:
        applied = apply_startup_file(search_path=os.environ[LAUNCH_PATH_VARIABLE], prune=prune)
    except ValueError as error:
        return StartupProblem(reason="failed", message=str(error))
    return AppliedView(added=list(applied.added), removed=list(applied.removed), failures=[failure.message for failure in applied.failures])
