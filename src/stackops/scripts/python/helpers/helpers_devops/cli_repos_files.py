from pathlib import Path
from typing import Annotated

import typer


def path_repositories(
    specs_path: Annotated[
        Path | None, typer.Option("--specs-path", "-s", help="Path to repos.json specification file."),
    ] = None,
) -> None:
    from stackops.utils.managed_file_cli import run_managed_file_action

    run_managed_file_action(kind="repos", action="path", path=specs_path)


def init_repositories(
    specs_path: Annotated[
        Path | None, typer.Option("--specs-path", "-s", help="Path to repos.json specification file."),
    ] = None,
) -> None:
    from stackops.utils.managed_file_cli import run_managed_file_action

    run_managed_file_action(kind="repos", action="init", path=specs_path)


def validate_repositories(
    specs_path: Annotated[
        Path | None, typer.Option("--specs-path", "-s", help="Path to repos.json specification file."),
    ] = None,
) -> None:
    from stackops.utils.managed_file_cli import run_managed_file_action

    run_managed_file_action(kind="repos", action="validate", path=specs_path)
