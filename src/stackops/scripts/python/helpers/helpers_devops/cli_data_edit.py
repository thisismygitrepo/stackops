from pathlib import Path
from typing import Annotated, Literal

import typer


def edit_data(
    path: Annotated[
        Path | None, typer.Option("--custom-path", "-p", help="Override the user configuration file path."),
    ] = None,
    editor: Annotated[Literal["hx", "nano", "code"], typer.Option("--editor", "-e", help="Editor to open the file with.")] = "hx",
    install_lsp: Annotated[bool, typer.Option("--install-lsp", "-l", help="Install the required language server if missing (Helix only).")] = False,
) -> None:
    from stackops.utils.managed_file_cli import run_managed_file_edit

    run_managed_file_edit(kind="data", path=path, editor=editor, install_lsp=install_lsp)
