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


def uninstall(
    which: Annotated[str, typer.Argument(help="Comma-separated program names.")],
    as_json: Annotated[bool, typer.Option("--json", "-j", help="Print what happened to each program as JSON.")] = False,
) -> None:
    import json

    from stackops.utils.installer_utils.installer_catalog import InstallerDataFileError
    from stackops.utils.installer_utils.installer_class import Installer
    from stackops.utils.installer_utils.installer_cli import INSTALLER_NAME_ALIASES
    from stackops.utils.installer_utils.installer_removal import BinaryKept, BinaryRemoved, remove_installed_binary
    from stackops.utils.installer_utils.installer_runner import get_installers_from_source
    from stackops.utils.schemas.installer.installer_types import get_normalized_arch, get_os_name

    try:
        installers = get_installers_from_source(source="all", user_path=None, os=get_os_name(), arch=get_normalized_arch(), which_cats=None)
    except InstallerDataFileError as error:
        typer.echo(f"""❌ {error}""", err=True)
        raise typer.Exit(code=1) from error
    installers_by_name = {installer["appName"].casefold(): installer for installer in installers}
    requested_names = [name.strip() for name in which.split(",") if name.strip() != ""]
    if len(requested_names) == 0:
        raise typer.BadParameter("at least one program name is required")
    # Every name is checked before anything is deleted. Only apps of the catalog can be named, so no other file in the install folder is reachable.
    unknown_names = [name for name in requested_names if INSTALLER_NAME_ALIASES.get(name.lower(), name).casefold() not in installers_by_name]
    if len(unknown_names) > 0:
        raise typer.BadParameter(f"""Unknown software name: {", ".join(unknown_names)}. Use software list to see the names. Nothing was deleted.""")

    outcomes: list[dict[str, str | bool | None]] = []
    for name in requested_names:
        installer = installers_by_name[INSTALLER_NAME_ALIASES.get(name.lower(), name).casefold()]
        exe_name = Installer(installer).get_exe_name()
        result = remove_installed_binary(exe_name=exe_name)
        match result:
            case BinaryRemoved():
                outcomes.append({"name": installer["appName"], "exe": exe_name, "path": str(result.path), "removed": True, "problem": ""})
            case BinaryKept():
                outcomes.append(
                    {
                        "name": installer["appName"],
                        "exe": exe_name,
                        "path": None if result.path is None else str(result.path),
                        "removed": False,
                        "problem": result.problem,
                    }
                )
    if as_json:
        typer.echo(json.dumps(outcomes, indent=2))
    else:
        for outcome in outcomes:
            typer.echo(f"""🗑️  Deleted {outcome["path"]} ({outcome["name"]})""" if outcome["removed"] else f"""⏭️  Kept {outcome["name"]}: {outcome["problem"]}""")
    if not all(outcome["removed"] for outcome in outcomes):
        raise typer.Exit(code=1)


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
    from stackops.utils.cli_utils.interaction import require_interactive
    from stackops.utils.installer_utils.installer_catalog import USER_INSTALLER_DATA_PATH, InstallerDataFileError
    from stackops.utils.installer_utils.installer_explore import explore_installers_by_category_labels
    from stackops.utils.installer_utils.installer_scripts import get_user_installer_scripts_root
    from stackops.utils.schemas.installer.installer_types import INSTALLER_DATA_SOURCE_MAP, InstallRequest

    require_interactive("Explore software; use devops software list --json and devops software install NAME")
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
