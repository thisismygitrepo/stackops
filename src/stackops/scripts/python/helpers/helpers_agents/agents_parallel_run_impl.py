from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_parallel_run_config import (
    PARALLEL_RUNS_SOURCE,
    ParallelCreateValues,
    ParallelYamlEntry,
    empty_parallel_create_values,
    ensure_parallel_yaml_exists,
    merge_parallel_create_values,
    parallel_yaml_format_explanation,
    ResolvedParallelCreateValues,
    resolve_parallel_yaml_paths,
)
from stackops.scripts.python.helpers.helpers_agents.agents_parallel_run_yaml import select_parallel_create_values_from_locations


def run_parallel_from_yaml(
    *,
    config_name: str | None,
    parallel_yaml_path: str | None,
    source: PARALLEL_RUNS_SOURCE,
    overrides: ParallelCreateValues,
    edit: bool,
    add_entry: bool,
    show_parallel_yaml_format: bool,
) -> None:
    yaml_locations = resolve_parallel_yaml_paths(parallel_yaml_path=parallel_yaml_path, source=source)
    created_yaml_paths: list[Path] = []
    if not add_entry:
        created_yaml_paths = _ensure_writable_parallel_yaml_files(
            yaml_locations=yaml_locations,
            parallel_yaml_path=parallel_yaml_path,
            source=source,
        )
    _report_created_yaml_paths(created_yaml_paths=created_yaml_paths)
    if add_entry:
        _add_parallel_yaml_entry(yaml_locations=yaml_locations, config_name=config_name)
        if show_parallel_yaml_format:
            import typer

            typer.echo(parallel_yaml_format_explanation(yaml_paths=yaml_locations))
        return
    if edit:
        _edit_existing_parallel_yaml_files(yaml_locations=yaml_locations)
    if show_parallel_yaml_format:
        import typer

        typer.echo(parallel_yaml_format_explanation(yaml_paths=yaml_locations))

    empty_overrides = empty_parallel_create_values()
    if (edit or add_entry or show_parallel_yaml_format or len(created_yaml_paths) > 0) and config_name is None and overrides == empty_overrides:
        return

    yaml_entries = _read_existing_parallel_yaml_entries(yaml_locations=yaml_locations)
    selected_entries = select_parallel_create_values_from_locations(yaml_entries=yaml_entries, requested_name=config_name)
    _reject_multi_run_collision_overrides(selected_entries=selected_entries, overrides=overrides)
    resolved_entries: list[tuple[str, ResolvedParallelCreateValues]] = []
    for selected_name, base_values in selected_entries:
        resolved = merge_parallel_create_values(base=base_values, overrides=overrides)
        require_explicit_parallel_context(selected_name=selected_name, resolved=resolved)
        resolved_entries.append((selected_name, resolved))
    _reject_duplicate_multi_run_outputs(resolved_entries=tuple(resolved_entries))

    from stackops.scripts.python.helpers.helpers_agents.agents_impl import agents_create

    for _selected_name, resolved in resolved_entries:
        agents_create(
            agent=resolved.agent,
            model=resolved.model,
            reasoning=resolved.reasoning_effort,
            provider=resolved.provider,
            host=resolved.host,
            context=resolved.context,
            context_path=resolved.context_path,
            separator=resolved.separator,
            agent_load=resolved.agent_load,
            stagger_max=resolved.stagger_max,
            prompt=resolved.prompt,
            prompt_path=resolved.prompt_path,
            prompt_name=resolved.prompt_name,
            job_name=resolved.job_name,
            join_prompt_and_context=resolved.join_prompt_and_context,
            run=resolved.run,
            output_path=resolved.output_path,
            agents_dir=resolved.agents_dir,
            save_as_yaml=False,
            interactive=resolved.interactive,
        )


def require_explicit_parallel_context(*, selected_name: str, resolved: ResolvedParallelCreateValues) -> None:
    if resolved.context is not None or resolved.context_path is not None:
        return
    raise ValueError(
        f"Parallel run '{selected_name}' does not define context or context_path. "
        "Add context_path to the YAML entry, or pass --context-path PATH when running it."
    )


def _reject_multi_run_collision_overrides(
    *, selected_entries: tuple[tuple[str, ParallelCreateValues], ...], overrides: ParallelCreateValues
) -> None:
    if len(selected_entries) < 2:
        return
    colliding_options: list[str] = []
    if overrides.job_name is not None:
        colliding_options.append("--job-name")
    if overrides.output_path is not None:
        colliding_options.append("--output-path")
    if overrides.agents_dir is not None:
        colliding_options.append("--agents-dir")
    if len(colliding_options) == 0:
        return
    joined_options = ", ".join(colliding_options)
    raise ValueError(f"{joined_options} cannot be used when multiple parallel runs are selected.")


def _reject_duplicate_multi_run_outputs(*, resolved_entries: tuple[tuple[str, ResolvedParallelCreateValues], ...]) -> None:
    if len(resolved_entries) < 2:
        return
    workspace_owner: dict[str, str] = {}
    layout_owner: dict[str, str] = {}
    for selected_name, resolved in resolved_entries:
        workspace_key = resolved.agents_dir if resolved.agents_dir is not None else f"job:{resolved.job_name}"
        layout_key = resolved.output_path if resolved.output_path is not None else f"workspace:{workspace_key}/layout.json"
        existing_workspace_owner = workspace_owner.get(workspace_key)
        if existing_workspace_owner is not None:
            raise ValueError(
                f"Parallel runs '{existing_workspace_owner}' and '{selected_name}' resolve to the same agents workspace. "
                "Give each selected YAML entry a distinct job_name or agents_dir."
            )
        existing_layout_owner = layout_owner.get(layout_key)
        if existing_layout_owner is not None:
            raise ValueError(
                f"Parallel runs '{existing_layout_owner}' and '{selected_name}' resolve to the same layout output. "
                "Give each selected YAML entry a distinct output_path."
            )
        workspace_owner[workspace_key] = selected_name
        layout_owner[layout_key] = selected_name


def edit_parallel_yaml(*, yaml_path: Path) -> None:
    import shutil
    import subprocess

    from stackops.scripts.python.helpers.helpers_agents.agents_yaml_schemas import ensure_stackops_yaml_schema_exists

    editor = shutil.which("hx")
    if editor is None:
        editor = shutil.which("nano")
    if editor is None:
        raise ValueError("No supported editor found. Install 'hx' or 'nano', or run without --edit")

    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    ensure_stackops_yaml_schema_exists(yaml_path=yaml_path, schema_kind="parallel")
    result = subprocess.run([editor, str(yaml_path)], check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Editor exited with status code {result.returncode}")


def _ensure_writable_parallel_yaml_files(
    *, yaml_locations: list[tuple[str, Path]], parallel_yaml_path: str | None, source: PARALLEL_RUNS_SOURCE
) -> list[Path]:
    created_yaml_paths: list[Path] = []
    for location_name, yaml_path in yaml_locations:
        should_create = _should_scaffold_parallel_yaml(location_name=location_name, parallel_yaml_path=parallel_yaml_path, source=source)
        if should_create and ensure_parallel_yaml_exists(yaml_path=yaml_path):
            created_yaml_paths.append(yaml_path)
    return created_yaml_paths


def _add_parallel_yaml_entry(*, yaml_locations: list[tuple[str, Path]], config_name: str | None) -> None:
    import typer
    from stackops.scripts.python.helpers.helpers_agents.agents_parallel_add_entry import add_parallel_yaml_entry

    target_yaml_path = _select_parallel_yaml_entry_target(yaml_locations=yaml_locations)
    added_entry_name = add_parallel_yaml_entry(yaml_path=target_yaml_path, entry_name=config_name)
    typer.echo(f"Added parallel YAML entry '{added_entry_name}' to: {target_yaml_path}")
    edit_parallel_yaml(yaml_path=target_yaml_path)


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


def _read_existing_parallel_yaml_entries(*, yaml_locations: list[tuple[str, Path]]) -> list[ParallelYamlEntry]:
    from stackops.utils.files.read import read_yaml

    yaml_entries: list[ParallelYamlEntry] = []
    for location_name, yaml_path in yaml_locations:
        if yaml_path.exists() and yaml_path.is_file():
            raw_data: object = read_yaml(yaml_path)
            yaml_entries.append((location_name, yaml_path, raw_data))
    if len(yaml_entries) == 0:
        searched = "\n".join(str(yaml_path) for _location_name, yaml_path in yaml_locations)
        raise ValueError(f"No parallel YAML files found. Searched:\n{searched}")
    return yaml_entries


def _select_parallel_yaml_entry_target(*, yaml_locations: list[tuple[str, Path]]) -> Path:
    for _location_name, yaml_path in yaml_locations:
        if yaml_path.exists() and yaml_path.is_file():
            return yaml_path
    return yaml_locations[0][1]


def _should_scaffold_parallel_yaml(*, location_name: str, parallel_yaml_path: str | None, source: PARALLEL_RUNS_SOURCE) -> bool:
    if parallel_yaml_path is not None:
        return True
    match source:
        case "all" | "a" | "repo" | "r":
            return location_name == "repo"
        case "private" | "p":
            return location_name == "private"
        case "public" | "b":
            return location_name == "public"
        case "library" | "l":
            return False
