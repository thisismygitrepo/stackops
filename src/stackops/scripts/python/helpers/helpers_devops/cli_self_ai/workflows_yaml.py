from collections.abc import Callable, Mapping
from pathlib import Path

import yaml

from stackops.scripts.python.helpers.helpers_agents.agents_parallel_run_config import (
    ParallelCreateValues,
    parallel_yaml_header_for_path,
    parallel_yaml_template,
)
from stackops.scripts.python.helpers.helpers_agents.agents_yaml_schemas import ensure_stackops_yaml_schema_exists
from stackops.scripts.python.helpers.helpers_devops.cli_self_ai import update_docs, update_installer, update_test
from stackops.scripts.python.helpers.helpers_devops.cli_self_ai.workflow_capture import WorkflowModule, capture_agents_create_values
from stackops.utils.accessories import get_repo_root


type ParallelWorkflowEntry = dict[str, object]


def write_workflows_to_yaml() -> Path:
    repo_root = _require_current_repo_root()
    yaml_path = repo_root / ".stackops" / "parallel.yaml"
    yaml_mapping = _load_parallel_yaml_mapping(yaml_path=yaml_path)
    yaml_mapping.update(_build_workflow_entries(repo_root=repo_root))
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    ensure_stackops_yaml_schema_exists(yaml_path=yaml_path, schema_kind="parallel")
    yaml_path.write_text(_render_parallel_yaml(yaml_path=yaml_path, yaml_mapping=yaml_mapping), encoding="utf-8")
    return yaml_path


def _require_current_repo_root() -> Path:
    repo_root = get_repo_root(Path.cwd())
    if repo_root is None:
        raise RuntimeError("Could not determine the repository root. Run this from inside a git repository.")
    return repo_root.resolve()


def _load_parallel_yaml_mapping(*, yaml_path: Path) -> dict[str, object]:
    raw_text = yaml_path.read_text(encoding="utf-8") if yaml_path.is_file() else parallel_yaml_template()
    loaded_yaml: object = yaml.safe_load(raw_text)
    if loaded_yaml is None:
        return {}
    if not isinstance(loaded_yaml, Mapping):
        raise ValueError(f"parallel YAML must be a mapping: {yaml_path}")

    yaml_mapping: dict[str, object] = {}
    for raw_key, raw_value in loaded_yaml.items():
        if not isinstance(raw_key, str):
            raise ValueError(f"parallel YAML contains a non-string top-level key: {raw_key!r}")
        yaml_mapping[raw_key] = raw_value
    return yaml_mapping


def _build_workflow_entries(*, repo_root: Path) -> dict[str, ParallelWorkflowEntry]:
    return {
        "update-installer": _build_captured_workflow_entry(
            repo_root=repo_root,
            workflow_module=update_installer,
            workflow_function=update_installer.update_installer,
            include_captured_context=False,
        ),
        "update-test": _build_captured_workflow_entry(
            repo_root=repo_root,
            workflow_module=update_test,
            workflow_function=update_test.update_test,
            include_captured_context=False,
        ),
        "update-docs": _build_captured_workflow_entry(
            repo_root=repo_root,
            workflow_module=update_docs,
            workflow_function=update_docs.update_docs,
            include_captured_context=False,
        ),
    }


def _build_captured_workflow_entry(
    *,
    repo_root: Path,
    workflow_module: WorkflowModule,
    workflow_function: Callable[[], None],
    include_captured_context: bool,
) -> ParallelWorkflowEntry:
    captured_values = capture_agents_create_values(workflow_module=workflow_module, workflow_function=workflow_function)
    job_name = _require_string(value=captured_values.job_name, field_name="job_name")
    context_path = _resolve_context_path(
        repo_root=repo_root,
        captured_values=captured_values,
        include_captured_context=include_captured_context,
    )
    entry: ParallelWorkflowEntry = {
        "agent": captured_values.agent,
        "model": captured_values.model,
        "reasoning_effort": captured_values.reasoning_effort,
        "provider": captured_values.provider,
        "host": captured_values.host,
        "separator": _yaml_separator_value(separator=_require_string(value=captured_values.separator, field_name="separator")),
        "agent_load": captured_values.agent_load,
        "prompt": captured_values.prompt,
        "prompt_path": captured_values.prompt_path,
        "prompt_name": captured_values.prompt_name,
        "job_name": job_name,
        "join_prompt_and_context": captured_values.join_prompt_and_context,
        "output_path": _normalize_cli_path(repo_root=repo_root, raw_path=captured_values.output_path),
        "agents_dir": _normalize_cli_path(repo_root=repo_root, raw_path=captured_values.agents_dir),
        "interactive": captured_values.interactive,
    }
    if context_path is not None:
        entry["context"] = None
        entry["context_path"] = context_path
    return entry


def _resolve_context_path(
    *,
    repo_root: Path,
    captured_values: ParallelCreateValues,
    include_captured_context: bool,
) -> str | None:
    if captured_values.context is not None:
        if include_captured_context:
            return captured_values.context
        return None

    context_path = _require_string(value=captured_values.context_path, field_name="context_path")
    normalized_path = _normalize_cli_path(repo_root=repo_root, raw_path=context_path)
    return _require_string(value=normalized_path, field_name="context_path")


def _require_string(*, value: str | None, field_name: str) -> str:
    if value is None:
        raise ValueError(f"Workflow must provide {field_name}")
    return value


def _normalize_cli_path(*, repo_root: Path, raw_path: str | None) -> str | None:
    if raw_path is None:
        return None

    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = repo_root / path
    try:
        return _repo_relative_cli_path(repo_root=repo_root, target_path=path.resolve())
    except ValueError:
        return str(path)


def _repo_relative_cli_path(*, repo_root: Path, target_path: Path) -> str:
    relative_path = target_path.relative_to(repo_root)
    return f"./{relative_path.as_posix()}"


def _yaml_separator_value(*, separator: str) -> str:
    return separator.encode("unicode_escape").decode("ascii")


def _render_parallel_yaml(*, yaml_path: Path, yaml_mapping: dict[str, object]) -> str:
    normalized_mapping = _normalize_separator_values(yaml_mapping=yaml_mapping)
    yaml_body = yaml.safe_dump(normalized_mapping, sort_keys=False, default_flow_style=False)
    return f"{parallel_yaml_header_for_path(yaml_path=yaml_path)}{yaml_body}"


def _normalize_separator_values(*, yaml_mapping: dict[str, object]) -> dict[str, object]:
    normalized_mapping: dict[str, object] = {}
    for entry_name, raw_entry in yaml_mapping.items():
        if not isinstance(raw_entry, dict):
            normalized_mapping[entry_name] = raw_entry
            continue

        normalized_entry: dict[object, object] = {}
        for raw_key, raw_value in raw_entry.items():
            if raw_key == "separator" and isinstance(raw_value, str) and "\n" in raw_value:
                normalized_entry[raw_key] = _yaml_separator_value(separator=raw_value)
            else:
                normalized_entry[raw_key] = raw_value
        normalized_mapping[entry_name] = normalized_entry
    return normalized_mapping


if __name__ == "__main__":
    yaml_path = write_workflows_to_yaml()
    print(f"Wrote parallel workflows to: {yaml_path}")
