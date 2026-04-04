"""Backup configuration types, parsing, and reading utilities."""

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TypedDict, cast

from rich.console import Console
from rich.panel import Panel
import yaml

from machineconfig.utils.source_of_truth import LIBRARY_ROOT
from machineconfig.profile.create_links_export import REPO_LOOSE

LIBRARY_BACKUP_PATH = LIBRARY_ROOT.joinpath("profile/mapper_data.yaml")
USER_BACKUP_PATH = Path.home().joinpath("dotfiles/machineconfig/mapper_data.yaml")
DEFAULT_BACKUP_HEADER = """# User-defined backup configuration
# Created by `devops data register`
#
# File structure:
# - Top-level mappings are groups (for example: dotfiles, history, secrets).
# - Each entry inside a group is one backup item.
#
# Entry format:
# example_group:
#   sample_item:
#     path_local: "~/path/to/local/file_or_directory"
#     path_cloud: "^"          # "^" lets machineconfig deduce a remote path from path_local
#     encrypt: true            # true/false
#     zip: false               # true/false
#     rel2home: true           # true: path_local is interpreted relative to your home dir
#     os:
#       - linux                # any | linux | darwin | windows
#
# Selection behavior:
# - `devops data sync` filters entries by the current OS using the `os` field.
# - You can target entries as:
#   - group name: "dotfiles"
#   - specific item: "dotfiles.bashrc"
#   - all entries: "all"
#
# Example:
# example_group:
#   sample_item:
#     path_local: "~/.config/example"
#     path_cloud: "^"
#     encrypt: true
#     zip: true
#     rel2home: true
#     os:
#       - linux
#       - darwin
"""
VALID_OS = frozenset({"any", "windows", "linux", "darwin"})
EXPECTED_BACKUP_FIELDS = frozenset({"path_local", "path_cloud", "zip", "encrypt", "rel2home", "os"})
OS_OUTPUT_ORDER = {"any": 0, "linux": 1, "darwin": 2, "windows": 3}


class BackupItem(TypedDict):
    path_local: str
    path_cloud: str | None
    zip: bool
    encrypt: bool
    rel2home: bool
    os: set[str]


BackupGroup = dict[str, BackupItem]
BackupConfig = dict[str, BackupGroup]
type BackupYamlItem = dict[str, str | bool | list[str]]
type BackupYamlGroup = dict[str, BackupYamlItem]
type BackupYamlDocument = dict[str, BackupYamlGroup]


def normalize_os_name(value: str) -> str:
    return value.strip().lower()


def _parse_os_field(os_field: object, item_name: str) -> set[str]:
    if os_field is None:
        raise ValueError(f"Backup entry '{item_name}' must define a non-empty 'os'.")
    if isinstance(os_field, Sequence) and not isinstance(os_field, str | bytes):
        raw_values = [str(item) for item in os_field]
    else:
        raise ValueError(f"Backup entry '{item_name}' must define 'os' as a YAML list.")
    values: set[str] = set()
    saw_any = False
    for raw in raw_values:
        token = normalize_os_name(raw)
        if not token:
            continue
        if token in {"any", "all", "*"}:
            saw_any = True
            continue
        if token not in VALID_OS:
            raise ValueError(f"Backup entry '{item_name}' has an invalid 'os' value: {os_field!r}.")
        values.add(token)
    if saw_any:
        if values:
            raise ValueError(f"Backup entry '{item_name}' cannot mix 'any' with specific OS values.")
        return {"any"}
    if not values:
        raise ValueError(f"Backup entry '{item_name}' must define a non-empty 'os'.")
    return values


def os_applies(os_values: set[str], system_name: str) -> bool:
    return "any" in os_values or system_name in os_values


def _parse_bool(value: object, field: str, item_name: str) -> bool:
    if isinstance(value, bool):
        return value
    raise ValueError(f"Backup entry '{item_name}' has an invalid '{field}' value.")


def _require_mapping(value: object, item_name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"Backup entry '{item_name}' must be a mapping.")
    return {str(key): item for key, item in value.items()}


def _require_str_field(raw: Mapping[str, object], field: str, item_name: str) -> str:
    value = raw.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Backup entry '{item_name}' must define a non-empty '{field}'.")
    return value.strip()


def _optional_str_field(raw: Mapping[str, object], field: str, item_name: str) -> str | None:
    if field not in raw:
        return None
    value = raw.get(field)
    if not isinstance(value, str):
        raise ValueError(f"Backup entry '{item_name}' has a non-string '{field}'.")
    token = value.strip()
    if not token:
        raise ValueError(f"Backup entry '{item_name}' has an empty '{field}'.")
    return token


def _require_bool_field(raw: Mapping[str, object], field: str, item_name: str) -> bool:
    if field not in raw:
        raise ValueError(f"Backup entry '{item_name}' must define '{field}'.")
    return _parse_bool(raw[field], field=field, item_name=item_name)


def _parse_backup_config(raw: Mapping[str, object]) -> BackupConfig:
    config: BackupConfig = {}
    for group_name, group_value in raw.items():
        group = _require_mapping(group_value, group_name)
        group_items: dict[str, BackupItem] = {}
        for item_name, value in group.items():
            item_key = f"{group_name}.{item_name}"
            item = _require_mapping(value, item_key)
            if "path" in item:
                raise ValueError(f"Backup entry '{item_key}' uses 'path'; use 'path_local' instead.")
            if "path_remote" in item:
                raise ValueError(f"Backup entry '{item_key}' uses 'path_remote'; use 'path_cloud' instead.")
            if "os_specific" in item:
                raise ValueError(f"Backup entry '{item_key}' uses 'os_specific'; use 'os' only.")
            unknown_fields = sorted(set(item) - EXPECTED_BACKUP_FIELDS)
            if unknown_fields:
                raise ValueError(f"Backup entry '{item_key}' has unsupported fields: {', '.join(unknown_fields)}.")
            group_items[item_name] = {
                "path_local": _require_str_field(item, "path_local", item_key),
                "path_cloud": _optional_str_field(item, "path_cloud", item_key),
                "zip": _require_bool_field(item, "zip", item_key),
                "encrypt": _require_bool_field(item, "encrypt", item_key),
                "rel2home": _require_bool_field(item, "rel2home", item_key),
                "os": _parse_os_field(item.get("os"), item_key),
            }
        if group_items:
            config[group_name] = group_items
    return config


def _load_backup_config(path: Path) -> BackupConfig:
    raw_value = cast(object, yaml.safe_load(path.read_text(encoding="utf-8")))
    if raw_value is None:
        return {}
    if not isinstance(raw_value, Mapping):
        raise ValueError(f"Backup configuration must be a mapping: {path}")
    return _parse_backup_config({str(key): item for key, item in raw_value.items()})


def _serialize_backup_config(config: BackupConfig) -> str:
    if not config:
        return DEFAULT_BACKUP_HEADER
    document: BackupYamlDocument = {}
    for group_name, group_items in config.items():
        yaml_group: BackupYamlGroup = {}
        for item_name, item in group_items.items():
            yaml_item: BackupYamlItem = {"path_local": item["path_local"]}
            path_cloud = item["path_cloud"]
            if path_cloud is not None:
                yaml_item["path_cloud"] = path_cloud
            yaml_item["encrypt"] = item["encrypt"]
            yaml_item["zip"] = item["zip"]
            yaml_item["rel2home"] = item["rel2home"]
            yaml_item["os"] = _serialize_os_values(item["os"])
            yaml_group[item_name] = yaml_item
        document[group_name] = yaml_group
    yaml_body = yaml.safe_dump(document, sort_keys=False, default_flow_style=False, allow_unicode=False, width=1000)
    return f"""{DEFAULT_BACKUP_HEADER}
{yaml_body}"""


def _serialize_os_values(os_values: set[str]) -> list[str]:
    return sorted(os_values, key=lambda value: OS_OUTPUT_ORDER[value])


def write_backup_config(path: Path, config: BackupConfig) -> None:
    path.write_text(_serialize_backup_config(config), encoding="utf-8")


def read_backup_config(repo: REPO_LOOSE) -> BackupConfig:
    match repo:
        case "library" | "l":
            path = LIBRARY_BACKUP_PATH
            bu_file = _load_backup_config(path)
        case "user" | "u":
            path = USER_BACKUP_PATH
            bu_file = _load_backup_config(path)
        case "all" | "a":
            console = Console()
            console.print(Panel(f"🧰 LOADING LIBRARY BACKUP CONFIGURATION\n📄 File: {LIBRARY_BACKUP_PATH}", title="[bold blue]Backup Configuration[/bold blue]", border_style="blue"))
            bu_library = _load_backup_config(LIBRARY_BACKUP_PATH)
            console.print(Panel(f"🧰 LOADING USER BACKUP CONFIGURATION\n📄 File: {USER_BACKUP_PATH}", title="[bold blue]Backup Configuration[/bold blue]", border_style="blue"))
            bu_user = _load_backup_config(USER_BACKUP_PATH)
            bu_file = {**bu_library, **bu_user}
        case _:
            raise ValueError(f"Invalid which_backup value: {repo!r}.")
    return bu_file
