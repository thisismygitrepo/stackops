from typing import Annotated, Never

import typer

from stackops.profile.linking.options import (
    CONFIG_SOURCE_LOOSE,
    CONFIG_SOURCE_MAP,
    DIRECTION_LOOSE,
    DIRECTION_MAP,
    METHOD_LOOSE,
    METHOD_MAP,
    SENSITIVITY_LOOSE,
    SENSITIVITY_MAP,
)
from stackops.profile.linking.conflict import ON_CONFLICT_LOOSE, ON_CONFLICT_MAPPER


def _exit_with_error(message: str) -> Never:
    typer.echo(typer.style("Error: ", fg=typer.colors.RED) + message)
    raise SystemExit(1)


def main_from_parser(
    direction: Annotated[
        DIRECTION_LOOSE,
        typer.Argument(..., help="Direction of sync: 'up' pushes default paths into the managed location, 'down' applies managed files back to default paths."),
    ],
    sensitivity: Annotated[SENSITIVITY_LOOSE, typer.Option(..., "--sensitivity", "-s", help="Sensitivity of the configuration files to manage.")] = "all",
    method: Annotated[METHOD_LOOSE, typer.Option(..., "--method", "-m", help="Method to use for linking files")] = "symlink",
    source: Annotated[CONFIG_SOURCE_LOOSE, typer.Option(..., "--source", "-S", help="Mapper source to use for config files.")] = "library",
    on_conflict: Annotated[ON_CONFLICT_LOOSE, typer.Option(..., "--on-conflict", "-c", help="Action to take on conflict")] = "throw-error",
    which: Annotated[str | None, typer.Option(..., "--which", "-w", help="Specific items to process ('all' for all items) (default is None, selection is interactive)")] = None,
) -> None:
    """Terminology:
    UP = Config-File-Default-Path -> Self-Managed-Config-File-Path
    DOWN = Self-Managed-Config-File-Path -> Config-File-Default-Path
    For public config files in the library repo, copy packaged settings first when syncing down."""
    from stackops.profile.create_links import ConfigMapper, read_mapper

    def merge_mapper_groups(
        private_mapper: dict[str, list[ConfigMapper]],
        public_mapper: dict[str, list[ConfigMapper]],
    ) -> dict[str, list[ConfigMapper]]:
        merged_mapper: dict[str, list[ConfigMapper]] = {
            program_name: list(program_files)
            for program_name, program_files in private_mapper.items()
        }
        for program_name, program_files in public_mapper.items():
            if program_name in merged_mapper:
                merged_mapper[program_name].extend(program_files)
                continue
            merged_mapper[program_name] = list(program_files)
        return merged_mapper

    source_key = CONFIG_SOURCE_MAP[source]
    mapper_full_obj = read_mapper(source=source_key)
    mapper_full: dict[str, list[ConfigMapper]]
    sensitivity_key = SENSITIVITY_MAP[sensitivity]
    if sensitivity_key == "private":
        mapper_full = mapper_full_obj["private"]
    elif sensitivity_key == "public":
        mapper_full = mapper_full_obj["public"]
    else:
        mapper_full = merge_mapper_groups(
            private_mapper=mapper_full_obj["private"],
            public_mapper=mapper_full_obj["public"],
        )
            
    if which is None:
        from stackops.utils.options_utils.tv_options import choose_from_dict_with_preview
        import pprint
        options_with_preview: dict[str, str] = {key: pprint.pformat(value, width=88, sort_dicts=True) for key, value in mapper_full.items()}
        items_chosen = choose_from_dict_with_preview(options_with_preview, extension="yaml", multi=True, preview_size_percent=75.0)
    else:
        which_stripped = which.strip()
        if which_stripped == "all":
            items_chosen = list(mapper_full.keys())
        else:
            items_chosen = [item.strip() for item in which_stripped.split(",")]
            if "" in items_chosen:
                _exit_with_error("--which contains an empty item.")
            unknown_items = [item for item in items_chosen if item not in mapper_full]
            if len(unknown_items) > 0:
                _exit_with_error(f"Unknown --which item(s): {', '.join(unknown_items)}")
    items_objects: dict[str, list[ConfigMapper]] = {item: mapper_full[item] for item in items_chosen}
    if len(items_objects) == 0:
        _exit_with_error("No valid items selected.")

    method_key = METHOD_MAP[method]
    from stackops.profile.create_links import apply_mapper

    apply_mapper(
        mapper_data=items_objects,
        on_conflict=ON_CONFLICT_MAPPER[on_conflict],
        method=method_key,
        direction=DIRECTION_MAP[direction],
    )
