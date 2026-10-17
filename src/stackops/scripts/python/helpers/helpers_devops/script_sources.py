from pathlib import Path

from stackops.scripts.python.helpers.helpers_search.script_help import SCRIPT_SOURCE


def get_script_locations(source: SCRIPT_SOURCE) -> dict[str, Path | str]:
    from stackops.utils.repos.stackops_paths import current_repo_stackops_path, require_current_repo_stackops_path
    from stackops.utils.source_of_truth import SCRIPTS_ROOT_LIBRARY, SCRIPTS_ROOT_PRIVATE, SCRIPTS_ROOT_PUBLIC

    dynamic_location = "https://github.com/thisismygitrepo/stackops/tree/main/src/stackops/jobs/scripts_dynamic"
    locations: dict[str, Path | str]
    match source:
        case "all" | "a":
            locations = {"private": SCRIPTS_ROOT_PRIVATE, "public": SCRIPTS_ROOT_PUBLIC, "library": SCRIPTS_ROOT_LIBRARY}
            repo_scripts = current_repo_stackops_path(path_kind="scripts")
            if repo_scripts is not None:
                locations = {"repo": repo_scripts, **locations}
            locations["dynamic"] = dynamic_location
        case "repo" | "r":
            locations = {"repo": require_current_repo_stackops_path(path_kind="scripts")}
        case "private" | "p":
            locations = {"private": SCRIPTS_ROOT_PRIVATE}
        case "public" | "b":
            locations = {"public": SCRIPTS_ROOT_PUBLIC}
        case "library" | "l":
            locations = {"library": SCRIPTS_ROOT_LIBRARY}
        case "dynamic" | "d":
            locations = {"dynamic": dynamic_location}
    return locations
