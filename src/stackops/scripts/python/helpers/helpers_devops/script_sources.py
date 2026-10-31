from pathlib import Path

from stackops.scripts.python.helpers.helpers_search.script_help import SCRIPT_SOURCE


def get_script_locations(source: SCRIPT_SOURCE) -> dict[str, Path | str]:
    from stackops.utils.repos.stackops_paths import current_workspace_stackops_paths, require_current_workspace_stackops_paths
    from stackops.utils.source_of_truth import SCRIPTS_ROOT_LIBRARY, SCRIPTS_ROOT_PRIVATE

    dynamic_location = "https://github.com/thisismygitrepo/stackops/tree/main/src/stackops/jobs/scripts_dynamic"
    locations: dict[str, Path | str]
    match source:
        case "all" | "a":
            locations = {label: path for label, path in current_workspace_stackops_paths(path_kind="scripts")}
            locations |= {"user": SCRIPTS_ROOT_PRIVATE, "library": SCRIPTS_ROOT_LIBRARY, "dynamic": dynamic_location}
        case "workspace" | "w":
            locations = {label: path for label, path in require_current_workspace_stackops_paths(path_kind="scripts")}
        case "user" | "u":
            locations = {"user": SCRIPTS_ROOT_PRIVATE}
        case "library" | "l":
            locations = {"library": SCRIPTS_ROOT_LIBRARY}
        case "dynamic" | "d":
            locations = {"dynamic": dynamic_location}
    return locations
