from pathlib import Path
from typing import Annotated, Literal

import typer

from stackops.utils.managed_files import ManagedFileKind

EDIT_HELP = "Create if missing, edit, and validate a StackOps user file and its schema."


def edit_managed_file(
    which: Annotated[ManagedFileKind, typer.Argument(help="Which managed file to edit.")],
    path: Annotated[
        Path | None,
        typer.Option("--custom-path", "-p", help="Edit a file of this kind at another path, e.g. a project-local .stackops/secrets/secrets.json."),
    ] = None,
    editor: Annotated[Literal["hx", "nano", "code"], typer.Option("--editor", "-e", help="Editor to open the file with.")] = "hx",
    install_lsp: Annotated[bool, typer.Option("--install-lsp", "-l", help="Install the required language server if missing (Helix only).")] = False,
) -> None:
    from stackops.utils.managed_file_cli import run_managed_file_edit

    run_managed_file_edit(kind=which, path=path, editor=editor, install_lsp=install_lsp)
