from pathlib import Path
from typing import Annotated, Literal, Never

import typer

from stackops.utils.managed_files import ManagedFileKind

EDIT_HELP = "Create if missing, edit, and validate a StackOps user file and its schema."


def _fail(message: str) -> Never:
    typer.echo(typer.style("Error: ", fg=typer.colors.RED) + message, err=True)
    raise typer.Exit(code=1)


def edit_managed_file(
    which: Annotated[ManagedFileKind, typer.Argument(help="Which managed file to edit.")],
    path: Annotated[
        Path | None,
        typer.Option("--custom-path", "-p", help="Edit a file of this kind at another path, e.g. a project-local .stackops/secrets/secrets.json."),
    ] = None,
    editor: Annotated[Literal["hx", "nano", "code"], typer.Option("--editor", "-e", help="Editor to open the file with.")] = "hx",
) -> None:
    import shutil
    import subprocess

    from stackops.utils.managed_file_operations import initialize_managed_file, validate_managed_file
    from stackops.utils.managed_files import get_managed_file_spec

    spec = get_managed_file_spec(which)
    file_path = spec.user_path if path is None else path.expanduser().resolve()
    if file_path.exists() and not file_path.is_file():
        _fail(f"Path exists but is not a file: {file_path}")
    editor_bin = shutil.which(editor)
    if editor_bin is None:
        _fail(f"Editor '{editor}' is not available on PATH.")

    try:
        initialize_managed_file(spec=spec, data_path=file_path)
        editor_command = [editor_bin, "--wait"] if editor == "code" else [editor_bin]
        result = subprocess.run([*editor_command, str(file_path)], check=False)
    except (OSError, ValueError) as exc:
        _fail(f"Could not edit {file_path}: {exc}")
    if result.returncode != 0:
        _fail(f"Editor exited with status code {result.returncode}.")
    try:
        validate_managed_file(kind=which, data_path=file_path)
    except (OSError, ValueError) as exc:
        _fail(f"Invalid configuration after editing: {exc}")
    typer.echo(f"""Validated: {file_path}""")
