from collections.abc import Mapping
from typing import cast, get_args

from stackops.scripts.python.helpers.helpers_agents.agents_parallel_run_config import (
    CREATE_CONFIG_KEYS,
    ParallelCreateValues,
)
from stackops.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AGENTS, HOST, PROVIDER
from stackops.scripts.python.helpers.helpers_agents.reasoning_capabilities import ReasoningEffort


def parse_parallel_create_values(*, raw_entry: object, entry_name: str) -> ParallelCreateValues:
    raw_mapping = _object_to_string_mapping(raw_value=raw_entry, label=f"parallel run '{entry_name}'")
    unknown_keys = sorted(key for key in raw_mapping if key not in CREATE_CONFIG_KEYS)
    if len(unknown_keys) > 0:
        joined_keys = ", ".join(unknown_keys)
        raise ValueError(f"Unknown keys in parallel run '{entry_name}': {joined_keys}")

    return ParallelCreateValues(
        agent=_optional_agent(mapping=raw_mapping, key="agent"),
        model=_optional_string(mapping=raw_mapping, key="model"),
        reasoning_effort=_optional_reasoning_effort(mapping=raw_mapping, key="reasoning_effort"),
        provider=_optional_provider(mapping=raw_mapping, key="provider"),
        host=_optional_host(mapping=raw_mapping, key="host"),
        context=_optional_string(mapping=raw_mapping, key="context"),
        context_path=_optional_string(mapping=raw_mapping, key="context_path"),
        separator=_optional_string(mapping=raw_mapping, key="separator"),
        agent_load=_optional_int(mapping=raw_mapping, key="agent_load"),
        prompt=_optional_string(mapping=raw_mapping, key="prompt"),
        prompt_path=_optional_string(mapping=raw_mapping, key="prompt_path"),
        prompt_name=_optional_string(mapping=raw_mapping, key="prompt_name"),
        job_name=_optional_string(mapping=raw_mapping, key="job_name"),
        join_prompt_and_context=_optional_bool(mapping=raw_mapping, key="join_prompt_and_context"),
        output_path=_optional_string(mapping=raw_mapping, key="output_path"),
        agents_dir=_optional_string(mapping=raw_mapping, key="agents_dir"),
        interactive=_optional_bool(mapping=raw_mapping, key="interactive"),
    )


def select_parallel_create_values(*, raw_data: object, requested_name: str | None) -> tuple[str, ParallelCreateValues]:
    if requested_name is not None:
        raw_entry = _resolve_named_entry(raw_data=raw_data, entry_name=requested_name)
        return requested_name, parse_parallel_create_values(raw_entry=raw_entry, entry_name=requested_name)

    from stackops.utils.options_utils.tv_options import choose_from_dict_with_preview

    candidates = _collect_entry_candidates(raw_data=raw_data, prefix="")
    if len(candidates) == 0:
        raise ValueError("No parallel run entries found in parallel YAML")
    chosen_name = choose_from_dict_with_preview(
        options_to_preview_mapping=candidates,
        extension="yaml",
        multi=False,
        preview_size_percent=45.0,
    )
    if chosen_name is None:
        raise SystemExit(1)
    raw_entry = _resolve_named_entry(raw_data=raw_data, entry_name=chosen_name)
    return chosen_name, parse_parallel_create_values(raw_entry=raw_entry, entry_name=chosen_name)


def select_parallel_create_values_from_locations(
    *, yaml_entries: list[tuple[str, object]], requested_name: str | None
) -> tuple[str, ParallelCreateValues]:
    if requested_name is not None:
        for _location_name, raw_data in yaml_entries:
            raw_entry = _try_resolve_named_entry(raw_data=raw_data, entry_name=requested_name)
            if raw_entry is not None:
                return requested_name, parse_parallel_create_values(raw_entry=raw_entry, entry_name=requested_name)
        raise ValueError(f"Parallel run '{requested_name}' was not found in parallel YAML")

    from stackops.utils.options_utils.tv_options import choose_from_dict_with_preview

    candidate_previews: dict[str, str] = {}
    candidate_sources: dict[str, tuple[str, object]] = {}
    use_location_prefix = len(yaml_entries) > 1
    for location_name, raw_data in yaml_entries:
        candidates = _collect_entry_candidates(raw_data=raw_data, prefix="")
        for candidate_name, candidate_preview in candidates.items():
            label = f"{location_name}.{candidate_name}" if use_location_prefix else candidate_name
            if label in candidate_previews:
                label = f"{label}@{location_name}"
            candidate_previews[label] = candidate_preview
            candidate_sources[label] = (candidate_name, raw_data)

    if len(candidate_previews) == 0:
        raise ValueError("No parallel run entries found in parallel YAML")
    chosen_label = choose_from_dict_with_preview(
        options_to_preview_mapping=candidate_previews,
        extension="yaml",
        multi=False,
        preview_size_percent=45.0,
    )
    if chosen_label is None:
        raise SystemExit(1)
    chosen_name, chosen_data = candidate_sources[chosen_label]
    raw_entry = _resolve_named_entry(raw_data=chosen_data, entry_name=chosen_name)
    return chosen_name, parse_parallel_create_values(raw_entry=raw_entry, entry_name=chosen_name)


def _object_to_string_mapping(*, raw_value: object, label: str) -> dict[str, object]:
    if not isinstance(raw_value, Mapping):
        raise ValueError(f"{label} must be a YAML mapping")
    result: dict[str, object] = {}
    for key, value in raw_value.items():
        if not isinstance(key, str):
            raise ValueError(f"{label} contains a non-string key: {key!r}")
        result[key] = value
    return result


def _resolve_named_entry(*, raw_data: object, entry_name: str) -> object:
    cursor = raw_data
    for segment in (part.strip() for part in entry_name.split(".")):
        if segment == "":
            continue
        mapping = _object_to_string_mapping(raw_value=cursor, label=f"parallel YAML segment before '{segment}'")
        if segment not in mapping:
            raise ValueError(f"Parallel run '{entry_name}' was not found in parallel YAML")
        cursor = mapping[segment]
    if cursor is None:
        raise ValueError(f"Parallel run '{entry_name}' points to null in parallel YAML")
    return cursor


def _try_resolve_named_entry(*, raw_data: object, entry_name: str) -> object | None:
    cursor = raw_data
    for segment in (part.strip() for part in entry_name.split(".")):
        if segment == "":
            continue
        if not isinstance(cursor, Mapping):
            return None
        mapping = _object_to_string_mapping(raw_value=cursor, label=f"parallel YAML segment before '{segment}'")
        if segment not in mapping:
            return None
        cursor = mapping[segment]
    if cursor is None:
        raise ValueError(f"Parallel run '{entry_name}' points to null in parallel YAML")
    return cursor


def _collect_entry_candidates(*, raw_data: object, prefix: str) -> dict[str, str]:
    if not isinstance(raw_data, Mapping):
        return {}
    raw_mapping = _object_to_string_mapping(raw_value=raw_data, label="parallel YAML")
    if prefix != "" and any(key in CREATE_CONFIG_KEYS for key in raw_mapping):
        return {prefix: _preview_entry(mapping=raw_mapping)}

    candidates: dict[str, str] = {}
    for key, value in raw_mapping.items():
        dotted_key = f"{prefix}.{key}" if prefix else key
        nested_candidates = _collect_entry_candidates(raw_data=value, prefix=dotted_key)
        for nested_key, nested_preview in nested_candidates.items():
            candidates[nested_key] = nested_preview
    return candidates


def _preview_entry(*, mapping: Mapping[str, object]) -> str:
    preview_lines: list[str] = []
    for key in ("agent", "job_name", "agent_load", "prompt", "prompt_path", "prompt_name", "context", "context_path"):
        value = mapping.get(key)
        if value is not None:
            preview_lines.append(f"{key}: {value}")
    if len(preview_lines) == 0:
        return "No create options configured."
    return "\n".join(preview_lines)


def _optional_string(*, mapping: Mapping[str, object], key: str) -> str | None:
    value = mapping.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string or null")
    return value


def _optional_bool(*, mapping: Mapping[str, object], key: str) -> bool | None:
    value = mapping.get(key)
    if value is None:
        return None
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be a boolean or null")
    return value


def _optional_int(*, mapping: Mapping[str, object], key: str) -> int | None:
    value = mapping.get(key)
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{key} must be an integer or null")
    return value


def _optional_agent(*, mapping: Mapping[str, object], key: str) -> AGENTS | None:
    value = _optional_string(mapping=mapping, key=key)
    if value is None:
        return None
    if value not in get_args(AGENTS):
        raise ValueError(f"{key} must be one of: {', '.join(get_args(AGENTS))}")
    return cast(AGENTS, value)


def _optional_host(*, mapping: Mapping[str, object], key: str) -> HOST | None:
    value = _optional_string(mapping=mapping, key=key)
    if value is None:
        return None
    if value not in get_args(HOST):
        raise ValueError(f"{key} must be one of: {', '.join(get_args(HOST))}")
    return cast(HOST, value)


def _optional_provider(*, mapping: Mapping[str, object], key: str) -> PROVIDER | None:
    value = _optional_string(mapping=mapping, key=key)
    if value is None:
        return None
    if value not in get_args(PROVIDER):
        raise ValueError(f"{key} must be one of: {', '.join(get_args(PROVIDER))}")
    return cast(PROVIDER, value)


def _optional_reasoning_effort(*, mapping: Mapping[str, object], key: str) -> ReasoningEffort | None:
    value = _optional_string(mapping=mapping, key=key)
    if value is None:
        return None
    if value not in get_args(ReasoningEffort):
        raise ValueError(f"{key} must be one of: {', '.join(get_args(ReasoningEffort))}")
    return cast(ReasoningEffort, value)
