from pathlib import Path

from stackops.scripts.python.helpers.helpers_devops.cli_interactive_picker import InteractivePickerOption, choose_interactive_options
from stackops.scripts.python.helpers.helpers_repos.spec_store import repo_record_path
from stackops.utils.schemas.repos.repos_types import RepoRecordDict


def select_repositories(repos: list[RepoRecordDict], which: str | None, interactive: bool) -> list[RepoRecordDict]:
    if which is None and not interactive:
        return repos

    selectors = [] if which is None else [selector.strip() for selector in which.split(",")]
    if which is not None:
        if any(not selector for selector in selectors):
            raise ValueError("--which requires non-empty repository names or full destination paths, separated by commas.")
        if "all" in selectors:
            if selectors != ["all"]:
                raise ValueError("--which 'all' cannot be combined with other selectors.")
            return repos

    destinations = [repo_record_path(repo) for repo in repos]
    selected_indices: set[int] = set()
    if interactive:
        options: list[InteractivePickerOption[int]] = []
        for index, (repo, destination) in enumerate(zip(repos, destinations, strict=True)):
            options.append(
                InteractivePickerOption(
                    value=index,
                    label=f"""{repo['name']} -> {destination} [{repo['sync']['mode']}]""",
                    preview=f"""# {repo['name']}

Destination: `{destination}`
Sync mode: `{repo['sync']['mode']}`
Recorded branch: `{repo['version']['branch']}`
Recorded commit: `{repo['version']['commit']}`
""",
                    disambiguator=destination.as_posix(),
                )
            )
        selected_indices.update(
            choose_interactive_options(
                options,
                missing_tool_message="Interactive repository selection requires `tv` on PATH.",
                missing_selection_message="Interactive selection did not map to a repository",
            )
        )
    else:
        for selector in selectors:
            matches = [index for index, repo in enumerate(repos) if repo["name"] == selector]
            if len(matches) > 1:
                matching_paths = ", ".join(destinations[index].as_posix() for index in matches)
                raise ValueError(f"""Ambiguous repository name '{selector}'. Use a full destination path: {matching_paths}""")
            if not matches:
                try:
                    selector_path = Path(selector).expanduser()
                except RuntimeError as error:
                    raise ValueError(f"""Cannot expand repository selector '{selector}': {error}""") from error
                if selector_path.is_absolute():
                    resolved_path = selector_path.resolve()
                    matches = [index for index, destination in enumerate(destinations) if destination == resolved_path]
            if not matches:
                raise ValueError(f"""Unknown repository selector: '{selector}'. Use a repository name or full destination path.""")
            selected_indices.update(matches)

    return [repo for index, repo in enumerate(repos) if index in selected_indices]
