from pathlib import Path
from typing import Annotated

import typer

from stackops.utils.schemas.installer.installer_types import InstallerDataSource


def install(
    ctx: typer.Context,
    which: Annotated[
        str | None,
        typer.Argument(help="Comma-separated program names, group names with --group, or category labels with --explore."),
    ] = None,
    group: Annotated[bool, typer.Option("--group", "-g", help="Treat names as package groups.")] = False,
    check: Annotated[bool, typer.Option("--check", "-c", help="Check installation status instead of installing.")] = False,
    source: Annotated[
        InstallerDataSource,
        typer.Option("--source", "-s", help="Catalog: library, user, or all. User entries override matching library names."),
    ] = "all",
    path: Annotated[Path | None, typer.Option("--path", "-p", help="Use another user catalog with --source user or all.")] = None,
    interactive: Annotated[bool, typer.Option("--interactive", "-i", help="Select programs interactively.")] = False,
    explore: Annotated[bool, typer.Option("--explore", "-x", help="Browse software by category before installing.")] = False,
    update: Annotated[bool, typer.Option("--update", "-u", help="Reinstall or upgrade installed apps when supported.")] = False,
    version: Annotated[str | None, typer.Option("--version", "-v", help="Install a specific version or tag when supported.")] = None,
) -> None:
    from stackops.utils.installer_utils import installer_cli
    from stackops.utils.installer_utils.installer_catalog import InstallerDataFileError

    if check:
        if path is not None:
            raise typer.BadParameter("--path cannot be used with --check; checks inspect installed executables")
        if which is None:
            raise typer.BadParameter("program name or group name is required when --check is set")
        installer_cli.check_installations(which=which, group=group)
        return

    try:
        installer_cli.main_installer_cli(
            ctx=ctx,
            which=which,
            group=group,
            source=source,
            path=path,
            interactive=interactive,
            explore=explore,
            update=update,
            version=version,
        )
    except InstallerDataFileError as error:
        typer.echo(f"""❌ {error}""", err=True)
        raise typer.Exit(code=1) from error
