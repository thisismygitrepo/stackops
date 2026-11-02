import json
from pathlib import Path
from typing import Annotated, Literal

import typer

from stackops.utils.schemas.installer.installer_types import INSTALLER_DATA_SOURCE_MAP, InstallerDataSource


def software_path(
    source: Annotated[InstallerDataSource, typer.Option("--source", "-s", help="Catalog paths to show: library, user, or all.")] = "all",
    path: Annotated[Path | None, typer.Option("--custom-path", "-p", help="Use another user catalog with --source user or all.")] = None,
) -> None:
    from stackops.utils.installer_utils.installer_scripts import LIBRARY_INSTALLER_SCRIPTS_ROOT, get_user_installer_scripts_root
    from stackops.utils.managed_file_operations import describe_managed_file
    from stackops.utils.managed_files import resolve_managed_file

    normalized_source = INSTALLER_DATA_SOURCE_MAP[source]
    if normalized_source == "library" and path is not None:
        raise typer.BadParameter("--custom-path requires --source user or all")
    spec, user_path = resolve_managed_file(kind="software", path=path)
    paths: dict[str, dict[str, str]] = {}
    if normalized_source in {"library", "all"}:
        paths["library"] = describe_managed_file(spec=spec, data_path=spec.example_source_path) | {"scripts": str(LIBRARY_INSTALLER_SCRIPTS_ROOT)}
    if normalized_source in {"user", "all"}:
        paths["user"] = describe_managed_file(spec=spec, data_path=user_path) | {"scripts": str(get_user_installer_scripts_root(user_catalog_path=user_path))}
    typer.echo(json.dumps(paths, indent=2))


def init_software(
    path: Annotated[Path | None, typer.Option("--custom-path", "-p", help="Create the user catalog at another path.")] = None,
    _source: Annotated[Literal["user"], typer.Option("--source", "-s", help="Catalog source to initialize. Only user is supported.")] = "user",
) -> None:
    from stackops.utils.managed_file_cli import run_managed_file_action

    run_managed_file_action(kind="software", action="init", path=path)


def edit_software(
    path: Annotated[Path | None, typer.Option("--custom-path", "-p", help="Edit the user catalog at another path.")] = None,
    _source: Annotated[Literal["user"], typer.Option("--source", "-s", help="Catalog source to edit. Only user is supported.")] = "user",
    editor: Annotated[Literal["hx", "nano", "code"], typer.Option("--editor", "-e", help="Editor to open the catalog with.")] = "hx",
) -> None:
    from stackops.utils.managed_file_cli import run_managed_file_edit

    run_managed_file_edit(kind="software", path=path, editor=editor)


def validate_software(
    path: Annotated[Path | None, typer.Option("--custom-path", "-p", help="Validate the user catalog at another path.")] = None,
    _source: Annotated[Literal["user"], typer.Option("--source", "-s", help="Catalog source to validate. Only user is supported.")] = "user",
) -> None:
    from stackops.utils.managed_file_cli import run_managed_file_action

    run_managed_file_action(kind="software", action="validate", path=path)
