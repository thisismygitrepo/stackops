from pathlib import Path
from typing import Annotated

import typer

from stackops.utils.managed_file_cli import run_managed_file_action
from stackops.utils.managed_files import ManagedFileKind


def config_path(
    which: Annotated[ManagedFileKind, typer.Argument(help="Which configuration file to locate.")],
    path: Annotated[Path | None, typer.Option("--path", "-p", help="Use an explicit configuration file path.")] = None,
) -> None:
    run_managed_file_action(kind=which, action="path", path=path)


def init_config(
    which: Annotated[ManagedFileKind, typer.Argument(help="Which configuration file to initialize.")],
    path: Annotated[Path | None, typer.Option("--path", "-p", help="Use an explicit configuration file path.")] = None,
) -> None:
    run_managed_file_action(kind=which, action="init", path=path)


def validate_config(
    which: Annotated[ManagedFileKind, typer.Argument(help="Which configuration file to validate.")],
    path: Annotated[Path | None, typer.Option("--path", "-p", help="Use an explicit configuration file path.")] = None,
) -> None:
    run_managed_file_action(kind=which, action="validate", path=path)
