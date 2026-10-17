import json
from pathlib import Path
from typing import Annotated

import typer

from stackops.utils.cli_utils.alias_markers import apply_alias_markers
from stackops.utils.cli_utils.ordered_group import ordered_group
from stackops.utils.schemas.installer.installer_types import InstallerDataSource


def list_software(
    query: Annotated[str | None, typer.Argument(help="Filter software by name, description, or category.")] = None,
    source: Annotated[
        InstallerDataSource,
        typer.Option("--source", "-s", help="Catalog: library, user, or all. User entries override matching library names."),
    ] = "all",
    path: Annotated[Path | None, typer.Option("--path", "-p", help="Use another user catalog with --source user or all.")] = None,
    as_json: Annotated[bool, typer.Option("--json", "-j", help="Print complete software definitions as JSON.")] = False,
) -> None:
    from rich.console import Console
    from rich.table import Table
    from rich.text import Text

    from stackops.utils.installer_utils.installer_catalog import InstallerDataFileError, read_installer_data

    try:
        installers = read_installer_data(source=source, user_path=path)
    except InstallerDataFileError as error:
        typer.echo(f"""❌ {error}""", err=True)
        raise typer.Exit(code=1) from error

    if query is not None:
        search = query.casefold()
        installers = [
            installer for installer in installers
            if search in " ".join((installer["appName"], installer["doc"], *installer["categoryLabels"])).casefold()
        ]
    installers.sort(key=lambda installer: installer["appName"].casefold())
    if as_json:
        typer.echo(json.dumps(installers, indent=2))
        return

    console = Console()
    if not installers:
        console.print("No software found in the selected catalog.")
        return
    table = Table(title=f"""Software catalog ({source}): {len(installers)} entries""")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Categories")
    table.add_column("Description", overflow="fold")
    for installer in installers:
        table.add_row(Text(installer["appName"]), Text(", ".join(installer["categoryLabels"])), Text(installer["doc"]))
    console.print(table)


def get_app() -> typer.Typer:
    from stackops.scripts.python.helpers.helpers_devops.cli_software_files import edit_software, init_software, software_path, validate_software
    from stackops.scripts.python.helpers.helpers_devops.cli_software_install import install

    app = typer.Typer(
        cls=ordered_group(("install", "list", "path", "init", "edit", "validate")),
        help="Install software and extend the bundled catalog with user definitions. Matching user names override library entries.",
        no_args_is_help=True,
        add_completion=False,
        context_settings={"help_option_names": ["-h", "--help"]},
    )
    app.command("install", no_args_is_help=True, help="📦 <i> Install software from the catalog.")(install)
    app.command("i", no_args_is_help=True, hidden=True)(install)
    app.command("list", help="📋 <l> List software definitions from the selected catalog.")(list_software)
    app.command("l", hidden=True)(list_software)
    app.command("path", help="📍 <p> Print catalog and schema paths as JSON.")(software_path)
    app.command("p", hidden=True)(software_path)
    app.command("init", help="📄 <I> Create an empty user catalog and its schema.")(init_software)
    app.command("I", hidden=True)(init_software)
    app.command("edit", help="📝 <e> Create, edit, and validate the user software catalog.")(edit_software)
    app.command("e", hidden=True)(edit_software)
    app.command("validate", help="✅ <v> Validate the user software catalog.")(validate_software)
    app.command("v", hidden=True)(validate_software)
    return apply_alias_markers(app)
