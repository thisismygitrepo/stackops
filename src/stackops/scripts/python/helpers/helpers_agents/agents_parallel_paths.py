from dataclasses import replace
from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_parallel_run_config import ParallelCreateValues


def resolve_parallel_create_paths(*, values: ParallelCreateValues, yaml_path: Path) -> ParallelCreateValues:
    catalog_path = yaml_path.expanduser().resolve()
    base_directory = catalog_path.parent
    if catalog_path.parts[-3:] == (".stackops", "agents", "parallel.yaml"):
        base_directory = catalog_path.parents[2]
    path_values: dict[str, str | None] = {
        "context_path": values.context_path,
        "prompt_path": values.prompt_path,
        "output_path": values.output_path,
        "agents_dir": values.agents_dir,
    }
    for field_name, raw_path in path_values.items():
        if raw_path is None:
            continue
        path = Path(raw_path).expanduser()
        if not path.is_absolute():
            path = base_directory / path
        path_values[field_name] = str(path.resolve())
    return replace(
        values,
        context_path=path_values["context_path"],
        prompt_path=path_values["prompt_path"],
        output_path=path_values["output_path"],
        agents_dir=path_values["agents_dir"],
    )
