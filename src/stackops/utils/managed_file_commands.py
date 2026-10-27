from pathlib import Path
from typing import Annotated

import typer

from stackops.utils.managed_files import ManagedFileKind


def register_managed_file_commands(
    *, app: typer.Typer, kind: ManagedFileKind, path_alias: str, init_alias: str, validate_alias: str,
) -> None:
    def path_file(
        path: Annotated[
            Path | None, typer.Option("--custom-path", "-p", help="Override the user configuration file path."),
        ] = None,
    ) -> None:
        from stackops.utils.managed_file_cli import run_managed_file_action

        run_managed_file_action(kind=kind, action="path", path=path)

    def init_file(
        path: Annotated[
            Path | None, typer.Option("--custom-path", "-p", help="Override the user configuration file path."),
        ] = None,
    ) -> None:
        from stackops.utils.managed_file_cli import run_managed_file_action

        run_managed_file_action(kind=kind, action="init", path=path)

    def validate_file(
        path: Annotated[
            Path | None, typer.Option("--custom-path", "-p", help="Override the user configuration file path."),
        ] = None,
    ) -> None:
        from stackops.utils.managed_file_cli import run_managed_file_action

        run_managed_file_action(kind=kind, action="validate", path=path)

    app.command("path", help=f"""📍 <{path_alias}> Print the configuration file and schema paths as JSON.""")(path_file)
    app.command(path_alias, hidden=True)(path_file)
    app.command("init", help=f"""🆕 <{init_alias}> Create a missing configuration file and its schema without opening an editor.""")(init_file)
    app.command(init_alias, hidden=True)(init_file)
    app.command("validate", help=f"""✅ <{validate_alias}> Validate the configuration file without opening an editor.""")(validate_file)
    app.command(validate_alias, hidden=True)(validate_file)
