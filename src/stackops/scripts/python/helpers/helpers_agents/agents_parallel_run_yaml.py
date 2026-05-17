from collections.abc import Mapping
from pathlib import Path
from typing import Final, cast, get_args

from stackops.scripts.python.helpers.helpers_agents.agents_parallel_yaml_defaults import ParallelCreateYamlEntry
from stackops.scripts.python.helpers.helpers_agents.agents_parallel_run_config import CREATE_CONFIG_KEYS, ParallelCreateValues, ParallelYamlEntry
from stackops.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AGENTS, HOST, PROVIDER
from stackops.scripts.python.helpers.helpers_agents.reasoning_capabilities import ReasoningEffort


PARALLEL_RUN_PREVIEW_SIZE_PERCENT: Final[float] = 70.0


def validate_parallel_run_name(*, entry_name: str) -> str:
    normalized_entry_name = entry_name.strip()
    if normalized_entry_name == "":
        raise ValueError("Parallel run name must not be empty")
    if "." in normalized_entry_name:
        raise ValueError("Parallel run names must be flat top-level YAML keys without dots")
    return normalized_entry_name


def parse_parallel_create_values(*, raw_entry: object, entry_name: str) -> ParallelCreateValues:
    raw_mapping = _object_to_string_mapping(raw_value=raw_entry, label=f"parallel run '{entry_name}'")
    unknown_keys = sorted(key for key in raw_mapping if key not in CREATE_CONFIG_KEYS)
    if len(unknown_keys) > 0:
        joined_keys = ", ".join(unknown_keys)
        raise ValueError(f"Unknown keys in parallel run '{entry_name}': {joined_keys}")

    parsed_entry: ParallelCreateYamlEntry = {
        "agent": _optional_agent(mapping=raw_mapping, key="agent"),
        "model": _optional_string(mapping=raw_mapping, key="model"),
        "reasoning": _optional_reasoning(mapping=raw_mapping, key="reasoning"),
        "provider": _optional_provider(mapping=raw_mapping, key="provider"),
        "host": _optional_host(mapping=raw_mapping, key="host"),
        "context": _optional_string(mapping=raw_mapping, key="context"),
        "context_path": _optional_string(mapping=raw_mapping, key="context_path"),
        "separator": _optional_string(mapping=raw_mapping, key="separator"),
        "agent_load": _optional_int(mapping=raw_mapping, key="agent_load"),
        "stagger_max": _optional_float(mapping=raw_mapping, key="stagger_max"),
        "prompt": _optional_string(mapping=raw_mapping, key="prompt"),
        "prompt_path": _optional_string(mapping=raw_mapping, key="prompt_path"),
        "prompt_name": _optional_string(mapping=raw_mapping, key="prompt_name"),
        "job_name": _optional_string(mapping=raw_mapping, key="job_name"),
        "join_prompt_and_context": _optional_bool(mapping=raw_mapping, key="join_prompt_and_context"),
        "run": _optional_bool(mapping=raw_mapping, key="run"),
        "output_path": _optional_string(mapping=raw_mapping, key="output_path"),
        "agents_dir": _optional_string(mapping=raw_mapping, key="agents_dir"),
        "interactive": _optional_bool(mapping=raw_mapping, key="interactive"),
    }

    return ParallelCreateValues(
        agent=parsed_entry["agent"],
        model=parsed_entry["model"],
        reasoning_effort=parsed_entry["reasoning"],
        provider=parsed_entry["provider"],
        host=parsed_entry["host"],
        context=parsed_entry["context"],
        context_path=parsed_entry["context_path"],
        separator=parsed_entry["separator"],
        agent_load=parsed_entry["agent_load"],
        stagger_max=parsed_entry["stagger_max"],
        prompt=parsed_entry["prompt"],
        prompt_path=parsed_entry["prompt_path"],
        prompt_name=parsed_entry["prompt_name"],
        job_name=parsed_entry["job_name"],
        join_prompt_and_context=parsed_entry["join_prompt_and_context"],
        run=parsed_entry["run"],
        output_path=parsed_entry["output_path"],
        agents_dir=parsed_entry["agents_dir"],
        interactive=parsed_entry["interactive"],
    )


def select_parallel_create_values(*, raw_data: object, requested_name: str | None) -> tuple[str, ParallelCreateValues]:
    if requested_name is not None:
        normalized_name = validate_parallel_run_name(entry_name=requested_name)
        raw_entry = _resolve_named_entry(raw_data=raw_data, entry_name=normalized_name)
        return normalized_name, parse_parallel_create_values(raw_entry=raw_entry, entry_name=normalized_name)

    from stackops.utils.options_utils.tv_options import choose_from_dict_with_preview

    candidates = _collect_entry_candidates(raw_data=raw_data)
    if len(candidates) == 0:
        raise ValueError("No parallel run entries found in parallel YAML")
    chosen_name = choose_from_dict_with_preview(
        options_to_preview_mapping=candidates, extension="yaml", multi=False, preview_size_percent=PARALLEL_RUN_PREVIEW_SIZE_PERCENT
    )
    if chosen_name is None:
        raise SystemExit(1)
    raw_entry = _resolve_named_entry(raw_data=raw_data, entry_name=chosen_name)
    return chosen_name, parse_parallel_create_values(raw_entry=raw_entry, entry_name=chosen_name)


def select_parallel_create_values_from_locations(
    *, yaml_entries: list[ParallelYamlEntry], requested_name: str | None
) -> tuple[str, ParallelCreateValues]:
    if requested_name is not None:
        normalized_name = validate_parallel_run_name(entry_name=requested_name)
        for _location_name, _yaml_path, raw_data in yaml_entries:
            raw_entry = _try_resolve_named_entry(raw_data=raw_data, entry_name=normalized_name)
            if raw_entry is not None:
                return normalized_name, parse_parallel_create_values(raw_entry=raw_entry, entry_name=normalized_name)
        raise ValueError(f"Parallel run '{normalized_name}' was not found in parallel YAML")

    from stackops.utils.options_utils.tv_options import choose_from_dict_with_preview

    candidate_previews: dict[str, str] = {}
    candidate_sources: dict[str, tuple[str, object]] = {}
    use_location_prefix = len(yaml_entries) > 1
    for location_name, yaml_path, raw_data in yaml_entries:
        candidates = _collect_entry_candidates(raw_data=raw_data)
        for candidate_name, candidate_preview in candidates.items():
            label = f"{location_name}:{candidate_name}" if use_location_prefix else candidate_name
            if label in candidate_previews:
                label = f"{label}@{location_name}"
            candidate_previews[label] = _preview_entry_from_path(preview=candidate_preview, yaml_path=yaml_path)
            candidate_sources[label] = (candidate_name, raw_data)

    if len(candidate_previews) == 0:
        raise ValueError("No parallel run entries found in parallel YAML")
    chosen_label = choose_from_dict_with_preview(
        options_to_preview_mapping=candidate_previews, extension="yaml", multi=False, preview_size_percent=PARALLEL_RUN_PREVIEW_SIZE_PERCENT
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
    mapping = _object_to_string_mapping(raw_value=raw_data, label="parallel YAML")
    if entry_name not in mapping:
        raise ValueError(f"Parallel run '{entry_name}' was not found in parallel YAML")
    resolved_entry = mapping[entry_name]
    if resolved_entry is None:
        raise ValueError(f"Parallel run '{entry_name}' points to null in parallel YAML")
    return resolved_entry


def _try_resolve_named_entry(*, raw_data: object, entry_name: str) -> object | None:
    if not isinstance(raw_data, Mapping):
        return None
    mapping = _object_to_string_mapping(raw_value=raw_data, label="parallel YAML")
    if entry_name not in mapping:
        return None
    resolved_entry = mapping[entry_name]
    if resolved_entry is None:
        raise ValueError(f"Parallel run '{entry_name}' points to null in parallel YAML")
    return resolved_entry


def _collect_entry_candidates(*, raw_data: object) -> dict[str, str]:
    if not isinstance(raw_data, Mapping):
        return {}
    raw_mapping = _object_to_string_mapping(raw_value=raw_data, label="parallel YAML")
    candidates: dict[str, str] = {}
    for key, value in raw_mapping.items():
        if not isinstance(value, Mapping):
            continue
        entry_mapping = _object_to_string_mapping(raw_value=value, label=f"parallel run '{key}'")
        if any(config_key in CREATE_CONFIG_KEYS for config_key in entry_mapping):
            candidates[key] = _preview_entry(mapping=entry_mapping)
    return candidates


def _preview_entry(*, mapping: Mapping[str, object]) -> str:
    preview_lines: list[str] = []
    for key in ("agent", "job_name", "agent_load", "stagger_max", "prompt", "prompt_path", "prompt_name", "context", "context_path"):
        value = mapping.get(key)
        if value is not None:
            preview_lines.append(f"{key}: {value}")
    if len(preview_lines) == 0:
        return "No create options configured."
    return "\n".join(preview_lines)


def _preview_entry_from_path(*, preview: str, yaml_path: Path) -> str:
    return f"source_yaml: {yaml_path}\n\n{preview}"


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


def _optional_float(*, mapping: Mapping[str, object], key: str) -> float | None:
    value = mapping.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{key} must be a number or null")
    return float(value)


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


def _optional_reasoning(*, mapping: Mapping[str, object], key: str) -> ReasoningEffort | None:
    value = _optional_string(mapping=mapping, key=key)
    if value is None:
        return None
    if value not in get_args(ReasoningEffort):
        raise ValueError(f"{key} must be one of: {', '.join(get_args(ReasoningEffort))}")
    return cast(ReasoningEffort, value)
