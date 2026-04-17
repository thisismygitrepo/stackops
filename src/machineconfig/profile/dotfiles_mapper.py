from collections.abc import Mapping
from pathlib import Path
from typing import Literal, NotRequired, TypedDict

import machineconfig.profile as profile_assets
import yaml

from machineconfig.utils.path_reference import get_path_reference_path


LIBRARY_MAPPER_PATH = get_path_reference_path(
    module=profile_assets,
    path_reference=profile_assets.MAPPER_DOTFILES_PATH_REFERENCE,
)
USER_MAPPER_PATH = Path.home().joinpath("dotfiles/machineconfig/mapper_dotfiles.yaml")
DEFAULT_DOTFILE_MAPPER_HEADER = (
    "# User-defined config file mappings\n"
    "# Created by `d c` CLI tool\n"
    "# os must be an explicit YAML list containing one or more of: linux, darwin, windows"
)

type OsName = Literal["linux", "darwin", "windows"]
type OsField = list[OsName]
type MapperSection = dict[str, "RawMapperEntry"]
type MapperDocument = dict[str, MapperSection]

ALL_OS_VALUES: tuple[OsName, OsName, OsName] = ("linux", "darwin", "windows")
DEFAULT_OS_FILTER = ",".join(ALL_OS_VALUES)
VALID_OS_VALUES: frozenset[OsName] = frozenset(ALL_OS_VALUES)
OS_OUTPUT_ORDER: dict[OsName, int] = {value: index for index, value in enumerate(ALL_OS_VALUES)}


class RawMapperEntry(TypedDict):
    original: str
    self_managed: str
    os: OsField
    contents: NotRequired[bool]
    copy: NotRequired[bool]


def _require_mapping(value: object, *, context: str) -> Mapping[object, object]:
    if isinstance(value, Mapping):
        return value
    raise TypeError(f"{context} must be a mapping, got {type(value).__name__}")


def _require_str(value: object, *, context: str) -> str:
    if isinstance(value, str):
        return value
    raise TypeError(f"{context} must be a string, got {type(value).__name__}")


def _require_bool(value: object, *, context: str) -> bool:
    if isinstance(value, bool):
        return value
    raise TypeError(f"{context} must be a boolean, got {type(value).__name__}")


def _require_os_name(value: object, *, context: str) -> OsName:
    token = _require_str(value, context=context).strip().lower()
    match token:
        case "darwin":
            return "darwin"
        case "linux":
            return "linux"
        case "windows":
            return "windows"
        case _:
            raise ValueError(f"{context} must be one of: {', '.join(ALL_OS_VALUES)}.")


def _normalize_os_values(raw_values: list[object], *, context: str) -> OsField:
    if len(raw_values) == 0:
        raise ValueError(f"{context} must contain at least one OS value.")
    seen: set[OsName] = set()
    for index, raw_value in enumerate(raw_values):
        token = _require_os_name(raw_value, context=f"{context}[{index}]")
        if token in seen:
            raise ValueError(f"{context} contains a duplicate OS value: {token}.")
        seen.add(token)
    return sorted(seen, key=OS_OUTPUT_ORDER.__getitem__)


def _require_os_field(value: object, *, context: str) -> OsField:
    if not isinstance(value, list):
        raise TypeError(f"{context} must be a YAML list[str], got {type(value).__name__}")
    return _normalize_os_values(list(value), context=context)


def normalize_os_filter(os_filter: str) -> OsField:
    tokens = [token.strip() for token in os_filter.split(",") if token.strip()]
    if len(tokens) == 0:
        raise ValueError("OS filter cannot be empty.")
    return _normalize_os_values(list(tokens), context="OS filter")


def _normalize_mapper_entry(entry_value: object, *, context: str) -> RawMapperEntry:
    entry_mapping = _require_mapping(entry_value, context=context)
    if "os" not in entry_mapping:
        raise ValueError(f"{context}.os is required.")
    normalized_entry: RawMapperEntry = {
        "original": _require_str(entry_mapping.get("original"), context=f"{context}.original"),
        "self_managed": _require_str(entry_mapping.get("self_managed"), context=f"{context}.self_managed"),
        "os": _require_os_field(entry_mapping.get("os"), context=f"{context}.os"),
    }
    if "contents" in entry_mapping:
        normalized_entry["contents"] = _require_bool(entry_mapping["contents"], context=f"{context}.contents")
    if "copy" in entry_mapping:
        normalized_entry["copy"] = _require_bool(entry_mapping["copy"], context=f"{context}.copy")
    return normalized_entry


def load_dotfiles_mapper(path: Path) -> MapperDocument:
    loaded_obj: object = yaml.safe_load(path.read_text(encoding="utf-8"))
    if loaded_obj is None:
        return {}
    root_mapping = _require_mapping(loaded_obj, context=f"{path}")
    normalized_document: MapperDocument = {}
    for section_name, section_value in root_mapping.items():
        section_name_str = _require_str(section_name, context=f"{path}.section")
        section_mapping = _require_mapping(section_value, context=f"{path}.{section_name_str}")
        normalized_section: MapperSection = {}
        for entry_name, entry_value in section_mapping.items():
            entry_name_str = _require_str(entry_name, context=f"{path}.{section_name_str}.entry")
            normalized_section[entry_name_str] = _normalize_mapper_entry(
                entry_value,
                context=f"{path}.{section_name_str}.{entry_name_str}",
            )
        normalized_document[section_name_str] = normalized_section
    return normalized_document


def dump_dotfiles_mapper(*, mapper: MapperDocument, header: str) -> str:
    if len(mapper) == 0:
        if len(header) == 0:
            return "{}\n"
        return f"{header.rstrip()}\n"
    yaml_body = yaml.safe_dump(mapper, sort_keys=False, default_flow_style=False)
    if len(header) == 0:
        return yaml_body
    return f"{header.rstrip()}\n\n{yaml_body}"


def write_dotfiles_mapper(*, path: Path, mapper: MapperDocument, header: str) -> None:
    path.write_text(dump_dotfiles_mapper(mapper=mapper, header=header), encoding="utf-8")
