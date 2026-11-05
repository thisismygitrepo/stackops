from pathlib import Path
from typing import Annotated, Literal

import typer


def edit_repositories(
    specs_path: Annotated[
        Path | None, typer.Option("--path", "-p", help="Path to repos.json specification file.")
    ] = None,
    editor: Annotated[
        Literal["nano", "hx", "code"], typer.Option("--editor", "-e", help="Editor to open repos.json. Defaults to hx.")
    ] = "hx",
    install_lsp: Annotated[bool, typer.Option("--install-lsp", "-l", help="Install the required language server if missing (Helix only).")] = False,
) -> None:
    from stackops.utils.managed_file_cli import run_managed_file_edit

    run_managed_file_edit(kind="repos", path=specs_path, editor=editor, install_lsp=install_lsp)
