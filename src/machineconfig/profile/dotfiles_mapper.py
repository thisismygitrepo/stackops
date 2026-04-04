from collections.abc import Mapping
from pathlib import Path
from typing import NotRequired, TypedDict

import yaml

from machineconfig.utils.source_of_truth import LIBRARY_ROOT


LIBRARY_MAPPER_PATH = LIBRARY_ROOT.joinpath("profile/mapper_dotfiles.yaml")
USER_MAPPER_PATH = Path.home().joinpath("dotfiles/machineconfig/mapper_dotfiles.yaml")
DEFAULT_DOTFILE_MAPPER_HEADER = "# User-defined config file mappings\n# Created by `d c` CLI tool"

type OsField = str | list[str]
type MapperSection = dict[str, "RawMapperEntry"]
type MapperDocument = dict[str, MapperSection]


class RawMapperEntry(TypedDict):
    original: str
    self_managed: str
    contents: NotRequired[bool]
    copy: NotRequired[bool]
    os: NotRequired[OsField]


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


def _require_os_field(value: object, *, context: str) -> OsField:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parsed_values: list[str] = []
        for index, item in enumerate(value):
            parsed_values.append(_require_str(item, context=f"{context}[{index}]"))
        return parsed_values
    raise TypeError(f"{context} must be a string or list[str], got {type(value).__name__}")


def normalize_os_filter(os_filter: str) -> OsField:
    tokens = [token.strip().lower() for token in os_filter.split(",") if token.strip()]
    if len(tokens) == 0:
        raise ValueError("OS filter cannot be empty.")
    if any(token in {"any", "all", "*"} for token in tokens):
        return "any"
    if len(tokens) == 1:
        return tokens[0]
    return tokens


def _normalize_mapper_entry(entry_value: object, *, context: str) -> RawMapperEntry:
    entry_mapping = _require_mapping(entry_value, context=context)
    normalized_entry: RawMapperEntry = {
        "original": _require_str(entry_mapping.get("original"), context=f"{context}.original"),
        "self_managed": _require_str(entry_mapping.get("self_managed"), context=f"{context}.self_managed"),
    }
    if "contents" in entry_mapping:
        normalized_entry["contents"] = _require_bool(entry_mapping["contents"], context=f"{context}.contents")
    if "copy" in entry_mapping:
        normalized_entry["copy"] = _require_bool(entry_mapping["copy"], context=f"{context}.copy")
    if "os" in entry_mapping:
        normalized_entry["os"] = _require_os_field(entry_mapping["os"], context=f"{context}.os")
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
