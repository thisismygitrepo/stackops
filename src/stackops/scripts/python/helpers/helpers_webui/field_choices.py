from collections import Counter
from platform import system
from typing import TypedDict

from stackops.profile.dotfiles_constants import ALL_OS_VALUES
from stackops.scripts.python.helpers.helpers_cloud.backup_config import os_applies, read_backup_config
from stackops.scripts.python.helpers.helpers_repos.spec_store import DEFAULT_REPOS_SPEC_PATH, load_repos_spec, repo_record_path
from stackops.scripts.python.helpers.helpers_webui.constants import EVERY_ITEM_CHOICE, FIELD_CHOICE_SOURCES, OPERATING_SYSTEM_TITLES, FieldChoiceSource
from stackops.utils.cloud.rclone import list_remote_names
from stackops.utils.source_of_truth import read_stackops_config_string


# What the app view's form shows in place of a text box. `labels` holds the text for each choice. `default` is what the command uses when the field is
# left alone; None keeps the default the CLI declares. `separator` joins several picks into the one value the CLI splits; it is empty for a single
# pick, and for a parameter that is repeated once per pick. `whole` is the choice that stands for all of them and is picked alone, or empty.
class FieldChoices(TypedDict):
    choices: list[str]
    labels: dict[str, str]
    default: str | None
    separator: str
    whole: str


def _cloud_choices(default: str | None) -> FieldChoices | None:
    try:
        names = list_remote_names()
    except RuntimeError:
        return None
    if len(names) == 0:
        return None
    return {"choices": list(names), "labels": {name: name for name in names}, "default": default, "separator": "", "whole": ""}


# The entries a backup run on this machine can name: the built-in list with the user's groups laid over it, less the entries for other systems.
def _backup_entry_choices() -> FieldChoices | None:
    try:
        library = read_backup_config(source="library")
        user = read_backup_config(source="user")
    except ValueError:
        return None
    current_system = system()
    selectors = [
        f"""{group_name}.{entry_name}"""
        for group_name, entries in {**(library or {}), **(user or {})}.items()
        for entry_name, entry in entries.items()
        if os_applies(entry["os"], system_name=current_system)
    ]
    if len(selectors) == 0:
        return None
    return {
        "choices": [EVERY_ITEM_CHOICE, *selectors],
        "labels": {EVERY_ITEM_CHOICE: "All", **{selector: selector for selector in selectors}},
        "default": None,
        "separator": ",",
        "whole": EVERY_ITEM_CHOICE,
    }


# A project goes by its name, or by its full path when another registered project has the same name: that is how the command tells them apart.
def _project_choices() -> FieldChoices | None:
    try:
        repos = load_repos_spec(path=DEFAULT_REPOS_SPEC_PATH)["repos"]
    except (OSError, ValueError):
        return None
    if len(repos) == 0:
        return None
    name_counts = Counter(repo["name"] for repo in repos)
    projects = [repo["name"] if name_counts[repo["name"]] == 1 else repo_record_path(repo).as_posix() for repo in repos]
    return {
        "choices": [EVERY_ITEM_CHOICE, *projects],
        "labels": {EVERY_ITEM_CHOICE: "All", **{project: project for project in projects}},
        "default": EVERY_ITEM_CHOICE,
        "separator": ",",
        "whole": EVERY_ITEM_CHOICE,
    }


def _read_source(source: FieldChoiceSource) -> FieldChoices | None:
    match source:
        case "default_cloud":
            try:
                default_cloud = read_stackops_config_string("default_rclone_config").strip()
            except (FileNotFoundError, KeyError, ValueError):
                default_cloud = ""
            return _cloud_choices(default=default_cloud)
        case "any_cloud":
            return _cloud_choices(default=None)
        case "backup_entries":
            return _backup_entry_choices()
        case "operating_systems":
            return {"choices": list(ALL_OS_VALUES), "labels": {value: OPERATING_SYSTEM_TITLES[value] for value in ALL_OS_VALUES}, "default": None, "separator": ",", "whole": ""}
        case "projects":
            return _project_choices()


# A field whose list is empty or cannot be read is left out, and so stays the text box it was.
def read_field_choices(path: str) -> dict[str, FieldChoices]:
    fields: dict[str, FieldChoices] = {}
    for name, source in FIELD_CHOICE_SOURCES.get(path, {}).items():
        field_choices = _read_source(source)
        if field_choices is not None:
            fields[name] = field_choices
    return fields
