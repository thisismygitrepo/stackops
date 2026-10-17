import json
from pathlib import Path
from typing import Annotated, Literal

import typer


def resolve_layout_file(*, layouts_file: Path | None, source: Literal["global", "local"] | None) -> Path:
    if layouts_file is not None and source is not None:
        raise typer.BadParameter("LAYOUTS_FILE cannot be combined with --source.")
    if layouts_file is not None:
        return layouts_file.expanduser().absolute()
    if source is None:
        raise typer.BadParameter("Provide LAYOUTS_FILE or --source global|local. Use terminal path to see both files.")
    from stackops.scripts.python.helpers.helpers_sessions.sessions_layout_source import default_layout_source_paths

    return default_layout_source_paths()[source]


def path_layouts(
    layouts_file: Annotated[
        Path | None, typer.Argument(dir_okay=False, help="Layout JSON file. Omit to show both global and current-directory paths."),
    ] = None,
    source: Annotated[
        Literal["global", "local"] | None,
        typer.Option("--source", "-s", help="Show one config file's paths. Cannot be combined with LAYOUTS_FILE."),
    ] = None,
) -> None:
    from stackops.utils.managed_file_cli import run_managed_file_action

    if layouts_file is not None or source is not None:
        file_path = resolve_layout_file(layouts_file=layouts_file, source=source)
        run_managed_file_action(kind="layouts", action="path", path=file_path)
        return

    from stackops.scripts.python.helpers.helpers_sessions.sessions_layout_source import default_layout_source_paths
    from stackops.utils.managed_file_operations import describe_managed_file
    from stackops.utils.managed_files import get_managed_file_spec

    spec = get_managed_file_spec("layouts")
    paths = {
        name: describe_managed_file(spec=spec, data_path=data_path)
        for name, data_path in default_layout_source_paths().items()
    }
    typer.echo(json.dumps(paths, indent=2))


def init_layouts(
    layouts_file: Annotated[
        Path | None, typer.Argument(dir_okay=False, help="Layout JSON file to create if missing."),
    ] = None,
    source: Annotated[
        Literal["global", "local"] | None,
        typer.Option("--source", "-s", help="Config file to initialize. Cannot be combined with LAYOUTS_FILE."),
    ] = None,
) -> None:
    from stackops.utils.managed_file_cli import run_managed_file_action

    file_path = resolve_layout_file(layouts_file=layouts_file, source=source)
    run_managed_file_action(kind="layouts", action="init", path=file_path)


def validate_layouts(
    layouts_file: Annotated[
        Path | None, typer.Argument(dir_okay=False, help="Layout JSON file to validate."),
    ] = None,
    source: Annotated[
        Literal["global", "local"] | None,
        typer.Option("--source", "-s", help="Config file to validate. Cannot be combined with LAYOUTS_FILE."),
    ] = None,
) -> None:
    from stackops.utils.managed_file_cli import run_managed_file_action

    file_path = resolve_layout_file(layouts_file=layouts_file, source=source)
    run_managed_file_action(kind="layouts", action="validate", path=file_path)
