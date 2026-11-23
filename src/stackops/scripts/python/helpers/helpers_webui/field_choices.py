from collections import Counter
from platform import system
from typing import Literal, TypedDict, cast, get_args

from stackops.profile.dotfiles_constants import ALL_OS_VALUES
from stackops.scripts.python.helpers.helpers_cloud.backup_config import os_applies, read_backup_config
from stackops.scripts.python.helpers.helpers_repos.spec_store import DEFAULT_REPOS_SPEC_PATH, load_repos_spec, repo_record_path
from stackops.scripts.python.helpers.helpers_webui.constants import EVERY_ITEM_CHOICE, FIELD_CHOICE_SOURCES, OPERATING_SYSTEM_TITLES, FieldChoiceSource
from stackops.utils.cloud.rclone import list_remote_names
from stackops.utils.source_of_truth import read_stackops_config_string


# What the app view's form shows in place of a text box. `labels` holds the text for each choice that is a name on this machine; a keyword of the
# CLI has none and is put into words by the form. `default` is what the command uses when the field is left alone; None keeps the default the CLI
# declares. `separator` joins several picks into the one value the CLI splits; it is empty for a single pick, and for a parameter that is repeated
# once per pick. `whole` is the choice that stands for all of them and is picked alone, or empty. `follows` names another parameter of the command
# whose value picks the list, and `choices_by` holds the list for each of its values, with `choices` left empty; both are empty for a list that is
# the same whatever else is set.
class FieldChoices(TypedDict):
    choices: list[str]
    labels: dict[str, str]
    default: str | None
    separator: str
    whole: str
    follows: str
    choices_by: dict[str, list[str]]


def _cloud_choices(default: str | None) -> FieldChoices | None:
    try:
        names = list_remote_names()
    except RuntimeError:
        return None
    if len(names) == 0:
        return None
    return {"choices": list(names), "labels": {name: name for name in names}, "default": default, "separator": "", "whole": "", "follows": "", "choices_by": {}}


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
        "follows": "",
        "choices_by": {},
    }


# A subset is cut from one backup list, so its entries follow the form's Source field. Entries for other systems stay in: a subset is often made
# for another machine.
def _backup_subset_choices() -> FieldChoices | None:
    sources: tuple[Literal["user", "library"], ...] = ("user", "library")
    selectors_by_source: dict[str, list[str]] = {}
    for source in sources:
        try:
            config = read_backup_config(source=source)
        except ValueError:
            continue
        selectors = [f"""{group_name}.{entry_name}""" for group_name, entries in (config or {}).items() for entry_name in entries]
        if len(selectors) > 0:
            selectors_by_source[source] = [EVERY_ITEM_CHOICE, *selectors]
    if len(selectors_by_source) == 0:
        return None
    return {
        "choices": [],
        "labels": {EVERY_ITEM_CHOICE: "All", **{selector: selector for selectors in selectors_by_source.values() for selector in selectors[1:]}},
        "default": None,
        "separator": ",",
        "whole": EVERY_ITEM_CHOICE,
        "follows": "source",
        "choices_by": selectors_by_source,
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
        "follows": "",
        "choices_by": {},
    }


# Saved profiles are kept per browser, so the list follows the form's Browser field. A browser with none saved is left out of `choices_by`.
def _browser_profile_choices(separator: str) -> FieldChoices | None:
    from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import ProfileBrowserName
    from stackops.scripts.python.helpers.helpers_agents.agents_browser_profile_listing import list_browser_profile_paths

    profiles_by_browser: dict[str, list[str]] = {}
    for browser in cast(tuple[ProfileBrowserName, ...], get_args(ProfileBrowserName)):
        try:
            profiles_by_browser[browser] = [path.name for path in list_browser_profile_paths(browser=browser)]
        except RuntimeError:
            continue
    if len(profiles_by_browser) == 0:
        return None
    return {
        "choices": [],
        "labels": {profile: profile for profiles in profiles_by_browser.values() for profile in profiles},
        "default": None,
        "separator": separator,
        "whole": "",
        "follows": "browser",
        "choices_by": profiles_by_browser,
    }


def _dotfile_group_choices() -> FieldChoices | None:
    import yaml

    from stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile_status_data import load_mappers

    try:
        mappers = load_mappers()
    except (OSError, TypeError, ValueError, yaml.YAMLError):
        return None
    groups = sorted({*mappers.user, *mappers.library, *mappers.catalog})
    if len(groups) == 0:
        return None
    return {"choices": groups, "labels": {group: group for group in groups}, "default": None, "separator": ",", "whole": "", "follows": "", "choices_by": {}}


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
        case "backup_subset_entries":
            return _backup_subset_choices()
        case "operating_systems":
            return {
                "choices": list(ALL_OS_VALUES), "labels": {value: OPERATING_SYSTEM_TITLES[value] for value in ALL_OS_VALUES},
                "default": None, "separator": ",", "whole": "", "follows": "", "choices_by": {},
            }
        case "projects":
            return _project_choices()
        case "browser_profiles":
            return _browser_profile_choices(separator=",")
        case "browser_profile":
            return _browser_profile_choices(separator="")
        case "dotfile_groups":
            return _dotfile_group_choices()
        case "config_agents" | "mcp_agents" | "doctor_agent" | "doctor_resources" | "reset_resources" | "agent_states" | "type_check_tools":
            from stackops.scripts.python.helpers.helpers_webui.field_choice_keywords import read_keyword_choices

            keywords = read_keyword_choices(source=source)
            return {
                "choices": list(keywords.choices), "labels": {}, "default": keywords.default, "separator": keywords.separator,
                "whole": keywords.whole, "follows": "", "choices_by": {},
            }


# A field whose list is empty or cannot be read is left out, and so stays the text box it was.
def read_field_choices(path: str) -> dict[str, FieldChoices]:
    fields: dict[str, FieldChoices] = {}
    for name, source in FIELD_CHOICE_SOURCES.get(path, {}).items():
        field_choices = _read_source(source)
        if field_choices is not None:
            fields[name] = field_choices
    return fields
