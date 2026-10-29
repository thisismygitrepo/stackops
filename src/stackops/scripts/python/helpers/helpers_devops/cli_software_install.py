from pathlib import Path
from typing import Annotated

import typer

from stackops.utils.schemas.installer.installer_types import InstallerDataSource


def install(
    ctx: typer.Context,
    which: Annotated[
        str | None,
        typer.Argument(help="Comma-separated program names, or group names with --group."),
    ] = None,
    group: Annotated[bool, typer.Option("--group", "-g", help="Treat names as package groups.")] = False,
    source: Annotated[
        InstallerDataSource,
        typer.Option("--source", "-s", help="Catalog: library, user, or all. User entries override matching library names."),
    ] = "all",
    path: Annotated[Path | None, typer.Option("--custom-path", "-p", help="Use another user catalog with --source user or all.")] = None,
    interactive: Annotated[bool, typer.Option("--interactive", "-i", help="Select programs interactively.")] = False,
    update: Annotated[bool, typer.Option("--update", "-u", help="Reinstall or upgrade installed apps when supported.")] = False,
    version: Annotated[str | None, typer.Option("--version", "-v", help="Install a specific version or tag when supported.")] = None,
) -> None:
    from stackops.utils.installer_utils import installer_cli
    from stackops.utils.installer_utils.installer_catalog import InstallerDataFileError

    try:
        installer_cli.main_installer_cli(
            ctx=ctx,
            which=which,
            group=group,
            source=source,
            path=path,
            interactive=interactive,
            update=update,
            version=version,
        )
    except InstallerDataFileError as error:
        typer.echo(f"""❌ {error}""", err=True)
        raise typer.Exit(code=1) from error


def explore(
    categories: Annotated[str | None, typer.Argument(help="Comma-separated category labels. Omit to choose categories interactively.")] = None,
    source: Annotated[
        InstallerDataSource,
        typer.Option("--source", "-s", help="Catalog: library, user, or all. User entries override matching library names."),
    ] = "all",
    path: Annotated[Path | None, typer.Option("--custom-path", "-p", help="Use another user catalog with --source user or all.")] = None,
    update: Annotated[bool, typer.Option("--update", "-u", help="Reinstall or upgrade installed apps when supported.")] = False,
    version: Annotated[str | None, typer.Option("--version", "-v", help="Install a specific version or tag when supported.")] = None,
) -> None:
    from stackops.utils.installer_utils.installer_catalog import USER_INSTALLER_DATA_PATH, InstallerDataFileError
    from stackops.utils.installer_utils.installer_explore import explore_installers_by_category_labels
    from stackops.utils.installer_utils.installer_scripts import get_user_installer_scripts_root
    from stackops.utils.schemas.installer.installer_types import INSTALLER_DATA_SOURCE_MAP, InstallRequest

    user_scripts_root = (
        None
        if INSTALLER_DATA_SOURCE_MAP[source] == "library"
        else get_user_installer_scripts_root(user_catalog_path=USER_INSTALLER_DATA_PATH if path is None else path.expanduser().absolute())
    )
    install_request = InstallRequest(version=version, update=update, user_scripts_root=user_scripts_root)
    category_labels = [item.strip() for item in categories.split(",") if item.strip()] if categories is not None else None
    try:
        explore_installers_by_category_labels(
            install_request=install_request,
            category_labels=category_labels,
            source=source,
            user_path=path,
        )
    except InstallerDataFileError as error:
        typer.echo(f"""❌ {error}""", err=True)
        raise typer.Exit(code=1) from error


def check(
    which: Annotated[str, typer.Argument(help="Comma-separated executable names, or a group name with --group.")],
    group: Annotated[bool, typer.Option("--group", "-g", help="Treat the name as a package group.")] = False,
) -> None:
    from stackops.utils.installer_utils.installer_cli import check_installations

    check_installations(which=which, group=group)
