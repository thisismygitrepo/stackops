from collections.abc import Mapping
from pathlib import Path

import yaml

from stackops.scripts.python.helpers.helpers_agents.agents_parallel_run_config import ensure_parallel_yaml_exists, parallel_yaml_header_for_path
from stackops.scripts.python.helpers.helpers_agents.agents_parallel_run_yaml import validate_parallel_run_name
from stackops.scripts.python.helpers.helpers_agents.agents_parallel_yaml_defaults import (
    ParallelCreateYamlEntry,
    PARALLEL_YAML_TEMPLATE_DEFAULT_ENTRY,
    PARALLEL_YAML_TEMPLATE_ENTRY_NAME,
)
from stackops.scripts.python.helpers.helpers_agents.agents_yaml_schemas import ensure_stackops_yaml_schema_exists


def add_parallel_yaml_entry(*, yaml_path: Path, entry_name: str | None) -> str:
    _ensure_parallel_yaml_file_exists_for_add_entry(yaml_path=yaml_path)
    yaml_text = yaml_path.read_text(encoding="utf-8")
    raw_data = yaml.safe_load(yaml_text)
    resolved_entry_name = _resolve_added_entry_name(raw_data=raw_data, requested_entry_name=entry_name)
    ensure_parallel_yaml_entry_exists(yaml_path=yaml_path, entry_name=resolved_entry_name)
    return resolved_entry_name


def ensure_parallel_yaml_entry_exists(*, yaml_path: Path, entry_name: str) -> bool:
    ensure_parallel_yaml_exists(yaml_path=yaml_path)
    resolved_entry_name = validate_parallel_run_name(entry_name=entry_name)
    yaml_text = yaml_path.read_text(encoding="utf-8")
    raw_data = yaml.safe_load(yaml_text)
    raw_mapping = _root_yaml_mapping(raw_data=raw_data)
    if resolved_entry_name in raw_mapping:
        return False

    updated_yaml_text = _append_top_level_parallel_entry(yaml_text=yaml_text, entry_name=resolved_entry_name)
    yaml_path.write_text(updated_yaml_text, encoding="utf-8")
    return True


def upsert_parallel_yaml_entry(*, yaml_path: Path, entry_name: str, entry_values: ParallelCreateYamlEntry) -> None:
    ensure_parallel_yaml_exists(yaml_path=yaml_path)
    resolved_entry_name = validate_parallel_run_name(entry_name=entry_name)
    yaml_text = yaml_path.read_text(encoding="utf-8")
    raw_data = yaml.safe_load(yaml_text)
    root_mapping = dict(_root_yaml_mapping(raw_data=raw_data))
    root_mapping[resolved_entry_name] = dict(entry_values)
    yaml_path.write_text(_render_parallel_yaml_mapping(yaml_path=yaml_path, root_mapping=root_mapping), encoding="utf-8")


def _ensure_parallel_yaml_file_exists_for_add_entry(*, yaml_path: Path) -> None:
    ensure_stackops_yaml_schema_exists(yaml_path=yaml_path, schema_kind="parallel")
    if yaml_path.exists():
        if not yaml_path.is_file():
            raise ValueError(f"parallel YAML path exists but is not a file: {yaml_path}")
        return
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    yaml_path.write_text(parallel_yaml_header_for_path(yaml_path=yaml_path), encoding="utf-8")


def _resolve_added_entry_name(*, raw_data: object, requested_entry_name: str | None) -> str:
    if requested_entry_name is not None:
        return requested_entry_name

    raw_mapping = _root_yaml_mapping(raw_data=raw_data)
    candidate_index = 1
    candidate_name = PARALLEL_YAML_TEMPLATE_ENTRY_NAME
    while candidate_name in raw_mapping:
        candidate_index += 1
        candidate_name = f"{PARALLEL_YAML_TEMPLATE_ENTRY_NAME}_{candidate_index}"
    return candidate_name


def _root_yaml_mapping(*, raw_data: object) -> Mapping[str, object]:
    if raw_data is None:
        return {}
    if not isinstance(raw_data, Mapping):
        raise ValueError("parallel YAML root must be a mapping")
    return raw_data


def _append_top_level_parallel_entry(*, yaml_text: str, entry_name: str) -> str:
    entry_block = _render_parallel_entry_block(entry_name=entry_name)
    stripped_yaml_text = yaml_text.rstrip()
    if stripped_yaml_text == "":
        return f"{entry_block}\n"
    return f"{stripped_yaml_text}\n\n{entry_block}\n"


def _render_parallel_entry_block(*, entry_name: str) -> str:
    entry_mapping = {entry_name: dict(PARALLEL_YAML_TEMPLATE_DEFAULT_ENTRY)}
    return yaml.safe_dump(entry_mapping, sort_keys=False, default_flow_style=False).rstrip()


def _render_parallel_yaml_mapping(*, yaml_path: Path, root_mapping: Mapping[str, object]) -> str:
    yaml_body = yaml.safe_dump(dict(root_mapping), sort_keys=False, default_flow_style=False)
    return f"{parallel_yaml_header_for_path(yaml_path=yaml_path)}{yaml_body}"
