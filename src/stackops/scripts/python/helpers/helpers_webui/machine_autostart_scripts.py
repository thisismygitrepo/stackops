import os
from pathlib import Path

from stackops.scripts.python.helpers.helpers_utils.autostart_script import StartupScriptFailure, StartupScriptFailureReason, add_startup_script
from stackops.scripts.python.helpers.helpers_webui.constants import LAUNCH_PATH_VARIABLE
from stackops.scripts.python.helpers.helpers_webui.machine_autostart_model import ProblemReason, StartupProblem
from stackops.scripts.python.helpers.helpers_webui.scripts_files import ScriptProblem, read_scripts

PROBLEM_OF_FAILURE: dict[StartupScriptFailureReason, ProblemReason] = {
    "unsupported_system": "unsupported",
    "unsupported_kind": "refused",
    "already_added": "refused",
    "not_added": "unknown_entry",
    "missing_program": "failed",
    "system_refused": "failed",
}


# Adding is what `utils machine autostart-add` does, through the command's own helper. The script is looked up in a fresh read of the places
# the Scripts page lists from `base_directory`, so the page can name nothing but a script StackOps keeps, whatever it sends. The script is
# given the PATH the web UI was started with, not this server's own, which uv has put its own folders in front of.
def add_tracked_script(base_directory: str, script_path: str) -> StartupProblem | None:
    listed = read_scripts(base_directory=base_directory)
    match listed:
        case ScriptProblem():
            return StartupProblem(reason="refused", message=listed.message)
        case _:
            tracked = any(script["path"] == script_path for place in listed["places"] for script in place["scripts"])
    if not tracked:
        return StartupProblem(reason="unknown_entry", message="That script is no longer among the ones StackOps keeps. It may have been renamed or removed.")
    result = add_startup_script(script_path=Path(script_path), search_path=os.environ[LAUNCH_PATH_VARIABLE])
    match result:
        case StartupScriptFailure():
            return StartupProblem(reason=PROBLEM_OF_FAILURE[result.reason], message=result.message)
        case _:
            return None
