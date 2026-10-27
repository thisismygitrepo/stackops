from pathlib import Path

from stackops.scripts.python.helpers.helpers_search.script_help import SCRIPT_SOURCE


def get_script_locations(source: SCRIPT_SOURCE) -> dict[str, Path | str]:
    from stackops.utils.repos.stackops_paths import current_repo_stackops_path, require_current_repo_stackops_path
    from stackops.utils.source_of_truth import SCRIPTS_ROOT_LIBRARY, SCRIPTS_ROOT_PRIVATE

    dynamic_location = "https://github.com/thisismygitrepo/stackops/tree/main/src/stackops/jobs/scripts_dynamic"
    locations: dict[str, Path | str]
    match source:
        case "all" | "a":
            locations = {"user": SCRIPTS_ROOT_PRIVATE, "library": SCRIPTS_ROOT_LIBRARY}
            project_scripts = current_repo_stackops_path(path_kind="scripts")
            if project_scripts is not None:
                locations = {"project": project_scripts, **locations}
            locations["dynamic"] = dynamic_location
        case "project" | "p":
            locations = {"project": require_current_repo_stackops_path(path_kind="scripts")}
        case "user" | "u":
            locations = {"user": SCRIPTS_ROOT_PRIVATE}
        case "library" | "l":
            locations = {"library": SCRIPTS_ROOT_LIBRARY}
        case "dynamic" | "d":
            locations = {"dynamic": dynamic_location}
    return locations
