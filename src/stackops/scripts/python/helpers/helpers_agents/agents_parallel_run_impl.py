import shutil
import subprocess
from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_parallel_run_config import (
    PARALLEL_RUNS_WHERE,
    ParallelCreateValues,
    empty_parallel_create_values,
    ensure_parallel_yaml_exists,
    merge_parallel_create_values,
    parallel_yaml_format_explanation,
    resolve_parallel_yaml_paths,
)
from stackops.scripts.python.helpers.helpers_agents.agents_parallel_run_yaml import select_parallel_create_values_from_locations


def run_parallel_from_yaml(
    *,
    config_name: str | None,
    parallel_yaml_path: str | None,
    where: PARALLEL_RUNS_WHERE,
    overrides: ParallelCreateValues,
    edit: bool,
    show_parallel_yaml_format: bool,
) -> None:
    yaml_locations = resolve_parallel_yaml_paths(parallel_yaml_path=parallel_yaml_path, where=where)
    created_yaml_paths = _ensure_writable_parallel_yaml_files(
        yaml_locations=yaml_locations,
        parallel_yaml_path=parallel_yaml_path,
        where=where,
    )
    _report_created_yaml_paths(created_yaml_paths=created_yaml_paths)
    if edit:
        _edit_existing_parallel_yaml_files(yaml_locations=yaml_locations)
    if show_parallel_yaml_format:
        import typer

        typer.echo(parallel_yaml_format_explanation(yaml_paths=yaml_locations))

    empty_overrides = empty_parallel_create_values()
    if (edit or show_parallel_yaml_format or len(created_yaml_paths) > 0) and config_name is None and overrides == empty_overrides:
        return

    yaml_entries = _read_existing_parallel_yaml_entries(yaml_locations=yaml_locations)
    _selected_name, base_values = select_parallel_create_values_from_locations(
        yaml_entries=yaml_entries,
        requested_name=config_name,
    )
    resolved = merge_parallel_create_values(base=base_values, overrides=overrides)

    from stackops.scripts.python.helpers.helpers_agents.agents_impl import agents_create

    agents_create(
        agent=resolved.agent,
        model=resolved.model,
        reasoning_effort=resolved.reasoning_effort,
        provider=resolved.provider,
        host=resolved.host,
        context=resolved.context,
        context_path=resolved.context_path,
        separator=resolved.separator,
        agent_load=resolved.agent_load,
        prompt=resolved.prompt,
        prompt_path=resolved.prompt_path,
        prompt_name=resolved.prompt_name,
        job_name=resolved.job_name,
        join_prompt_and_context=resolved.join_prompt_and_context,
        output_path=resolved.output_path,
        agents_dir=resolved.agents_dir,
        interactive=resolved.interactive,
    )


def edit_parallel_yaml(*, yaml_path: Path) -> None:
    editor = shutil.which("hx")
    if editor is None:
        editor = shutil.which("nano")
    if editor is None:
        raise ValueError("No supported editor found. Install 'hx' or 'nano', or run without --edit")

    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run([editor, str(yaml_path)], check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Editor exited with status code {result.returncode}")


def _ensure_writable_parallel_yaml_files(
    *, yaml_locations: list[tuple[str, Path]], parallel_yaml_path: str | None, where: PARALLEL_RUNS_WHERE
) -> list[Path]:
    created_yaml_paths: list[Path] = []
    has_existing_yaml = any(yaml_path.exists() and yaml_path.is_file() for _location_name, yaml_path in yaml_locations)
    for location_name, yaml_path in yaml_locations:
        should_create = (
            parallel_yaml_path is not None
            or (where in ("all", "a") and not has_existing_yaml and location_name == "repo")
            or (where in ("repo", "r") and location_name == "repo")
            or (where in ("private", "p", "public", "b") and location_name in ("private", "public"))
        )
        if should_create and ensure_parallel_yaml_exists(yaml_path=yaml_path):
            created_yaml_paths.append(yaml_path)
    return created_yaml_paths


def _report_created_yaml_paths(*, created_yaml_paths: list[Path]) -> None:
    if len(created_yaml_paths) == 0:
        return
    import typer

    for created_yaml_path in created_yaml_paths:
        typer.echo(f"Created parallel YAML template at: {created_yaml_path}")


def _edit_existing_parallel_yaml_files(*, yaml_locations: list[tuple[str, Path]]) -> None:
    editable_locations = [(name, path) for name, path in yaml_locations if path.exists() and path.is_file()]
    for _location_name, yaml_path in editable_locations:
        edit_parallel_yaml(yaml_path=yaml_path)


def _read_existing_parallel_yaml_entries(*, yaml_locations: list[tuple[str, Path]]) -> list[tuple[str, object]]:
    from stackops.utils.files.read import read_yaml

    yaml_entries: list[tuple[str, object]] = []
    for location_name, yaml_path in yaml_locations:
        if yaml_path.exists() and yaml_path.is_file():
            raw_data: object = read_yaml(yaml_path)
            yaml_entries.append((location_name, raw_data))
    if len(yaml_entries) == 0:
        searched = "\n".join(str(yaml_path) for _location_name, yaml_path in yaml_locations)
        raise ValueError(f"No parallel YAML files found. Searched:\n{searched}")
    return yaml_entries
