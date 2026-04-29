from typing import Annotated, Literal, TypeAlias

import typer


ON_CONFLICT_LOOSE: TypeAlias = Literal[
    "throw-error", "t",
    "overwrite-self-managed", "os",
    "backup-self-managed", "bs",
    "overwrite-default-path", "od",
    "backup-default-path", "bd"
    ]
ON_CONFLICT_STRICT: TypeAlias = Literal["throw-error", "overwrite-self-managed", "backup-self-managed", "overwrite-default-path", "backup-default-path"]
ON_CONFLICT_MAPPER: dict[ON_CONFLICT_LOOSE, ON_CONFLICT_STRICT] = {
    "t": "throw-error",
    "os": "overwrite-self-managed",
    "bs": "backup-self-managed",
    "od": "overwrite-default-path",
    "bd": "backup-default-path",
    "throw-error": "throw-error",
    "overwrite-self-managed": "overwrite-self-managed",
    "backup-self-managed": "backup-self-managed",
    "overwrite-default-path": "overwrite-default-path",
    "backup-default-path": "backup-default-path",
    }

SENSITIVITY_LOOSE: TypeAlias = Literal["private", "p", "public", "b", "all", "a"]
SENSITIVITY_STRICT: TypeAlias = Literal["private", "public", "all"]
SENSITIVITY_MAP: dict[SENSITIVITY_LOOSE, SENSITIVITY_STRICT] = {
    "private": "private",
    "p": "private",
    "public": "public",
    "b": "public",
    "all": "all",
    "a": "all",
}

REPO_STRICT: TypeAlias = Literal["library", "user", "all"]
REPO_LOOSE: TypeAlias = Literal["library", "l", "user", "u", "all", "a"]
REPO_MAP: dict[REPO_LOOSE, REPO_STRICT] = {
    "library": "library",
    "l": "library",
    "user": "user",
    "u": "user",
    "a": "all",
    "all": "all",
}

METHOD_STRICT: TypeAlias = Literal["symlink", "copy"]
METHOD_LOOSE: TypeAlias = Literal["symlink", "s", "copy", "c"]
METHOD_MAP: dict[METHOD_LOOSE, METHOD_STRICT] = {
    "symlink": "symlink",
    "s": "symlink",
    "copy": "copy",
    "c": "copy",
}

DIRECTION_LOOSE: TypeAlias = Literal["up", "u", "down", "d"]
DIRECTION_STRICT: TypeAlias = Literal["up", "down"]
DIRECTION_MAP: dict[DIRECTION_LOOSE, DIRECTION_STRICT] = {
    "up": "up",
    "u": "up",
    "down": "down",
    "d": "down",
}



def main_from_parser(
    direction: Annotated[
        DIRECTION_LOOSE,
        typer.Argument(..., help="Direction of sync: 'up' pushes default paths into the managed location, 'down' applies managed files back to default paths."),
    ],
    sensitivity: Annotated[SENSITIVITY_LOOSE, typer.Option(..., "--sensitivity", "-s", help="Sensitivity of the configuration files to manage.")],
    method: Annotated[METHOD_LOOSE, typer.Option(..., "--method", "-m", help="Method to use for linking files")],
    repo: Annotated[REPO_LOOSE, typer.Option(..., "--repo", "-r", help="Mapper source to use for config files.")] = "library",
    on_conflict: Annotated[ON_CONFLICT_LOOSE, typer.Option(..., "--on-conflict", "-c", help="Action to take on conflict")] = "throw-error",
    which: Annotated[str | None, typer.Option(..., "--which", "-w", help="Specific items to process ('all' for all items) (default is None, selection is interactive)")] = None,
) -> None:
    """Terminology:
    UP = Config-File-Default-Path -> Self-Managed-Config-File-Path
    DOWN = Self-Managed-Config-File-Path -> Config-File-Default-Path
    For public config files in the library repo, copy packaged settings first when syncing down."""
    from stackops.profile.create_links import ConfigMapper, read_mapper

    repo_key = REPO_MAP[repo]
    mapper_full_obj = read_mapper(repo=repo_key)
    mapper_full: dict[str, list[ConfigMapper]]
    if sensitivity in {"private", "p"}:
        mapper_full = mapper_full_obj["private"]
    elif sensitivity in {"public", "b"}:
        mapper_full = mapper_full_obj["public"]
    else:
        mapper_full = {**mapper_full_obj["private"], **mapper_full_obj["public"]}
            
    if which is None:
        from stackops.utils.options_utils.tv_options import choose_from_dict_with_preview
        import pprint
        options_with_preview: dict[str, str] = {key: pprint.pformat(value, width=88, sort_dicts=True) for key, value in mapper_full.items()}
        items_chosen = choose_from_dict_with_preview(options_with_preview, extension="yaml", multi=True, preview_size_percent=75.0)
    else:
        if which == "all":
            items_chosen = list(mapper_full.keys())
        else:
            items_chosen = which.split(",")
    items_objections: dict[str, list[ConfigMapper]] = {item: mapper_full[item] for item in items_chosen if item in mapper_full}
    if len(items_objections) == 0:
        msg = typer.style("Error: ", fg=typer.colors.RED) + "No valid items selected."
        typer.echo(msg)
        raise typer.Exit(code=1)

    method = METHOD_MAP[method]
    from stackops.profile.create_links import apply_mapper

    apply_mapper(
        mapper_data=items_objections,
        on_conflict=ON_CONFLICT_MAPPER[on_conflict],
        method=method,
        direction=DIRECTION_MAP[direction],
    )
