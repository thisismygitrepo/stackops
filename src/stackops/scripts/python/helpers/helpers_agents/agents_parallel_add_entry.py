import sys
from collections.abc import Generator, Mapping
from contextlib import contextmanager
from pathlib import Path
from stat import S_IMODE
from tempfile import TemporaryDirectory
from typing import cast

import yaml

from stackops.scripts.python.helpers.helpers_agents.agents_parallel_run_config import ensure_parallel_yaml_exists, parallel_yaml_header_for_path
from stackops.scripts.python.helpers.helpers_agents.agents_parallel_run_yaml import validate_parallel_run_name
from stackops.scripts.python.helpers.helpers_agents.agents_parallel_yaml_defaults import (
    ParallelCreateYamlEntry,
    PARALLEL_YAML_TEMPLATE_ENTRY_NAME,
    parallel_yaml_default_entry,
)
from stackops.utils.managed_files import ensure_managed_schema, get_managed_file_spec


def add_parallel_yaml_entry(*, yaml_path: Path, entry_name: str | None) -> str:
    created = ensure_parallel_yaml_exists(yaml_path=yaml_path)
    yaml_text = yaml_path.read_text(encoding="utf-8")
    raw_data = yaml.safe_load(yaml_text)
    if created:
        resolved_entry_name = validate_parallel_run_name(entry_name=entry_name if entry_name is not None else PARALLEL_YAML_TEMPLATE_ENTRY_NAME)
        if resolved_entry_name != PARALLEL_YAML_TEMPLATE_ENTRY_NAME:
            root_mapping = dict(_root_yaml_mapping(raw_data=raw_data))
            root_mapping[resolved_entry_name] = root_mapping.pop(PARALLEL_YAML_TEMPLATE_ENTRY_NAME)
            yaml_path.write_text(_render_parallel_yaml_mapping(yaml_path=yaml_path, root_mapping=root_mapping), encoding="utf-8")
        return resolved_entry_name
    resolved_entry_name = _resolve_added_entry_name(raw_data=raw_data, requested_entry_name=entry_name)
    ensure_parallel_yaml_entry_exists(yaml_path=yaml_path, entry_name=resolved_entry_name)
    return resolved_entry_name


def ensure_parallel_yaml_entry_exists(*, yaml_path: Path, entry_name: str) -> bool:
    ensure_parallel_yaml_exists(yaml_path=yaml_path)
    resolved_entry_name = validate_parallel_run_name(entry_name=entry_name)
    yaml_text = yaml_path.read_text(encoding="utf-8")
    raw_data = yaml.safe_load(yaml_text)
    root_mapping = dict(_root_yaml_mapping(raw_data=raw_data))
    if resolved_entry_name in root_mapping:
        return False

    root_mapping[resolved_entry_name] = parallel_yaml_default_entry()
    yaml_path.write_text(_render_parallel_yaml_mapping(yaml_path=yaml_path, root_mapping=root_mapping), encoding="utf-8")
    return True


def upsert_parallel_yaml_entry(*, yaml_path: Path, entry_name: str, entry_values: ParallelCreateYamlEntry) -> None:
    resolved_entry_name = validate_parallel_run_name(entry_name=entry_name)
    spec = get_managed_file_spec("parallel")
    target = yaml_path.resolve()
    with _parallel_yaml_save_lock(target):
        ensure_managed_schema(spec=spec, data_path=yaml_path)
        if target.exists():
            source = target
            mode = S_IMODE(target.stat().st_mode)
        else:
            source = spec.example_source_path
            mode = spec.file_mode
        raw_data = yaml.safe_load(source.read_text(encoding="utf-8"))
        root_mapping = dict(_root_yaml_mapping(raw_data=raw_data))
        root_mapping[resolved_entry_name] = dict(entry_values)
        with TemporaryDirectory(dir=target.parent) as directory:
            replacement = Path(directory) / target.name
            replacement.write_text(_render_parallel_yaml_mapping(yaml_path=yaml_path, root_mapping=root_mapping), encoding="utf-8")
            replacement.chmod(mode)
            replacement.replace(target)


@contextmanager
def _parallel_yaml_save_lock(target: Path) -> Generator[None]:
    target.parent.mkdir(parents=True, exist_ok=True)
    # Keep a stable lock file so waiting writers share the same lock across catalog replacements.
    with target.with_name(f".{target.name}.lock").open("a+b") as lock:
        if sys.platform == "win32":
            import msvcrt

            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(lock, fcntl.LOCK_EX)
        yield


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


def _root_yaml_mapping(*, raw_data: object) -> Mapping[object, object]:
    if raw_data is None:
        return {}
    if not isinstance(raw_data, Mapping):
        raise ValueError("parallel YAML root must be a mapping")
    return cast(Mapping[object, object], raw_data)


def _render_parallel_yaml_mapping(*, yaml_path: Path, root_mapping: Mapping[object, object]) -> str:
    yaml_body = yaml.safe_dump(dict(root_mapping), sort_keys=False, default_flow_style=False)
    return f"{parallel_yaml_header_for_path(yaml_path=yaml_path)}{yaml_body}"
