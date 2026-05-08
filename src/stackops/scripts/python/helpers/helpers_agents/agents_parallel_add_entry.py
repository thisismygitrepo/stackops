from collections.abc import Mapping
from pathlib import Path

import yaml

from stackops.scripts.python.helpers.helpers_agents.agents_parallel_run_config import ensure_parallel_yaml_exists, parallel_yaml_header_for_path
from stackops.scripts.python.helpers.helpers_agents.agents_parallel_yaml_defaults import (
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
    entry_segments = _entry_name_segments(entry_name=entry_name)
    yaml_text = yaml_path.read_text(encoding="utf-8")
    raw_data = yaml.safe_load(yaml_text)
    existing_prefix_length = _existing_prefix_length(raw_data=raw_data, entry_segments=entry_segments, entry_name=entry_name)
    if existing_prefix_length == len(entry_segments):
        return False

    if existing_prefix_length == 0:
        updated_yaml_text = _append_top_level_parallel_entry(yaml_text=yaml_text, entry_segments=entry_segments)
    else:
        updated_yaml_text = _insert_nested_parallel_entry(
            yaml_text=yaml_text,
            prefix_segments=entry_segments[:existing_prefix_length],
            missing_segments=entry_segments[existing_prefix_length:],
        )

    yaml_path.write_text(updated_yaml_text, encoding="utf-8")
    return True


def _ensure_parallel_yaml_file_exists_for_add_entry(*, yaml_path: Path) -> None:
    ensure_stackops_yaml_schema_exists(yaml_path=yaml_path, schema_kind="parallel")
    if yaml_path.exists():
        if not yaml_path.is_file():
            raise ValueError(f"parallel YAML path exists but is not a file: {yaml_path}")
        return
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    yaml_path.write_text(parallel_yaml_header_for_path(yaml_path=yaml_path), encoding="utf-8")


def _entry_name_segments(*, entry_name: str) -> list[str]:
    entry_segments = [segment.strip() for segment in entry_name.split(".") if segment.strip() != ""]
    if len(entry_segments) == 0:
        raise ValueError("CONFIG_NAME must contain at least one non-empty path segment")
    return entry_segments


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


def _existing_prefix_length(*, raw_data: object, entry_segments: list[str], entry_name: str) -> int:
    if raw_data is None:
        return 0
    cursor = raw_data
    for index, entry_segment in enumerate(entry_segments):
        if not isinstance(cursor, Mapping):
            existing_prefix = ".".join(entry_segments[:index])
            raise ValueError(
                f"Cannot add parallel run '{entry_name}' under '{existing_prefix}' because that YAML node is not a mapping"
            )
        if entry_segment not in cursor:
            return index
        cursor = cursor[entry_segment]
    return len(entry_segments)


def _append_top_level_parallel_entry(*, yaml_text: str, entry_segments: list[str]) -> str:
    entry_block = _render_parallel_entry_block(entry_segments=entry_segments, base_indent=0)
    stripped_yaml_text = yaml_text.rstrip()
    if stripped_yaml_text == "":
        return f"{entry_block}\n"
    return f"{stripped_yaml_text}\n\n{entry_block}\n"


def _insert_nested_parallel_entry(*, yaml_text: str, prefix_segments: list[str], missing_segments: list[str]) -> str:
    yaml_lines = yaml_text.splitlines()
    insert_index, child_indent = _find_mapping_insert_location(yaml_lines=yaml_lines, prefix_segments=prefix_segments)
    entry_block = _render_parallel_entry_block(entry_segments=missing_segments, base_indent=child_indent)
    updated_yaml_lines = yaml_lines[:insert_index] + entry_block.splitlines() + yaml_lines[insert_index:]
    return "\n".join(updated_yaml_lines).rstrip() + "\n"


def _render_parallel_entry_block(*, entry_segments: list[str], base_indent: int) -> str:
    nested_entry = _nested_parallel_entry(entry_segments=entry_segments)
    dumped_yaml = yaml.safe_dump(nested_entry, sort_keys=False, default_flow_style=False).rstrip()
    if base_indent == 0:
        return dumped_yaml
    indentation = " " * base_indent
    return "\n".join(indentation + line if line != "" else line for line in dumped_yaml.splitlines())


def _nested_parallel_entry(*, entry_segments: list[str]) -> dict[str, object]:
    nested_entry: dict[str, object] = dict(PARALLEL_YAML_TEMPLATE_DEFAULT_ENTRY)
    for entry_segment in reversed(entry_segments):
        nested_entry = {entry_segment: nested_entry}
    return nested_entry


def _find_mapping_insert_location(*, yaml_lines: list[str], prefix_segments: list[str]) -> tuple[int, int]:
    search_start_index = 0
    search_end_index = len(yaml_lines)
    current_indent = 0
    for prefix_segment in prefix_segments:
        located_mapping = _find_mapping_block(
            yaml_lines=yaml_lines,
            segment=prefix_segment,
            indent=current_indent,
            search_start_index=search_start_index,
            search_end_index=search_end_index,
        )
        if located_mapping is None:
            joined_prefix = ".".join(prefix_segments)
            raise ValueError(f"Could not locate YAML mapping for '{joined_prefix}'")
        _line_index, block_end_index, child_indent = located_mapping
        search_start_index = _line_index + 1
        search_end_index = block_end_index
        current_indent = child_indent
    return search_end_index, current_indent


def _find_mapping_block(
    *,
    yaml_lines: list[str],
    segment: str,
    indent: int,
    search_start_index: int,
    search_end_index: int,
) -> tuple[int, int, int] | None:
    for line_index in range(search_start_index, search_end_index):
        line = yaml_lines[line_index]
        if _line_is_blank_or_comment(line=line):
            continue
        if _line_indent(line=line) != indent:
            continue
        stripped_line = line[indent:]
        if not stripped_line.startswith(f"{segment}:"):
            continue
        trailing_text = stripped_line[len(segment) + 1 :]
        if trailing_text.strip() != "" and not trailing_text.lstrip().startswith("#"):
            raise ValueError(
                f"Cannot add nested parallel run under '{segment}' because that YAML node uses an inline value"
            )
        block_end_index = _mapping_block_end_index(
            yaml_lines=yaml_lines,
            parent_indent=indent,
            search_start_index=line_index + 1,
            search_end_index=search_end_index,
        )
        child_indent = _infer_child_indent(
            yaml_lines=yaml_lines,
            parent_indent=indent,
            search_start_index=line_index + 1,
            search_end_index=block_end_index,
        )
        return line_index, block_end_index, child_indent
    return None


def _mapping_block_end_index(*, yaml_lines: list[str], parent_indent: int, search_start_index: int, search_end_index: int) -> int:
    for line_index in range(search_start_index, search_end_index):
        line = yaml_lines[line_index]
        if _line_is_blank_or_comment(line=line):
            continue
        if _line_indent(line=line) <= parent_indent:
            return line_index
    return search_end_index


def _infer_child_indent(*, yaml_lines: list[str], parent_indent: int, search_start_index: int, search_end_index: int) -> int:
    for line_index in range(search_start_index, search_end_index):
        line = yaml_lines[line_index]
        if _line_is_blank_or_comment(line=line):
            continue
        line_indent = _line_indent(line=line)
        if line_indent > parent_indent:
            return line_indent
    return parent_indent + 2


def _line_is_blank_or_comment(*, line: str) -> bool:
    stripped_line = line.strip()
    return stripped_line == "" or stripped_line.startswith("#")


def _line_indent(*, line: str) -> int:
    return len(line) - len(line.lstrip(" "))
