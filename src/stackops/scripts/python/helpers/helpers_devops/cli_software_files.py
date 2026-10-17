import json
from pathlib import Path
from typing import Annotated, Literal

import typer

from stackops.utils.schemas.installer.installer_types import INSTALLER_DATA_SOURCE_MAP, InstallerDataSource


def software_path(
    source: Annotated[InstallerDataSource, typer.Option("--source", "-s", help="Catalog paths to show: library, user, or all.")] = "all",
    path: Annotated[Path | None, typer.Option("--path", "-p", help="Use another user catalog with --source user or all.")] = None,
) -> None:
    from stackops.utils.installer_utils.installer_scripts import LIBRARY_INSTALLER_SCRIPTS_ROOT, get_user_installer_scripts_root
    from stackops.utils.managed_file_operations import describe_managed_file
    from stackops.utils.managed_files import get_managed_file_spec

    normalized_source = INSTALLER_DATA_SOURCE_MAP[source]
    if normalized_source == "library" and path is not None:
        raise typer.BadParameter("--path requires --source user or all")
    spec = get_managed_file_spec("software")
    paths: dict[str, dict[str, str]] = {}
    if normalized_source in {"library", "all"}:
        paths["library"] = describe_managed_file(spec=spec, data_path=spec.example_source_path) | {"scripts": str(LIBRARY_INSTALLER_SCRIPTS_ROOT)}
    if normalized_source in {"user", "all"}:
        user_path = spec.user_path if path is None else path.expanduser().absolute()
        paths["user"] = describe_managed_file(spec=spec, data_path=user_path) | {"scripts": str(get_user_installer_scripts_root(user_catalog_path=user_path))}
    typer.echo(json.dumps(paths, indent=2))


def init_software(
    path: Annotated[Path | None, typer.Option("--path", "-p", help="Create the user catalog at another path.")] = None,
) -> None:
    from stackops.utils.managed_file_cli import run_managed_file_action

    run_managed_file_action(kind="software", action="init", path=path)


def edit_software(
    path: Annotated[Path | None, typer.Option("--path", "-p", help="Edit the user catalog at another path.")] = None,
    editor: Annotated[Literal["hx", "nano", "code"], typer.Option("--editor", "-e", help="Editor to open the catalog with.")] = "hx",
) -> None:
    from stackops.scripts.python.helpers.helpers_devops.cli_config_edit import edit_managed_file

    edit_managed_file(which="software", path=path, editor=editor)


def validate_software(
    path: Annotated[Path | None, typer.Option("--path", "-p", help="Validate the user catalog at another path.")] = None,
) -> None:
    from stackops.utils.managed_file_cli import run_managed_file_action

    run_managed_file_action(kind="software", action="validate", path=path)
