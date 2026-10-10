from pathlib import Path
from typing import Annotated, Literal, Never

import typer

from stackops.utils.managed_files import ManagedFileKind

EDIT_HELP = "Open a StackOps user file in an editor, creating a minimal one with its schema when missing."


def _fail(message: str) -> Never:
    typer.echo(typer.style("Error: ", fg=typer.colors.RED) + message)
    raise typer.Exit(code=1)


def edit_managed_file(
    which: Annotated[ManagedFileKind, typer.Argument(help="Which managed file to edit.")],
    path: Annotated[
        Path | None,
        typer.Option("--path", "-p", help="Edit a file of this kind at another path, e.g. a project-local .stackops/secrets/secrets.json."),
    ] = None,
    editor: Annotated[Literal["hx", "nano", "code"], typer.Option("--editor", "-e", help="Editor to open the file with.")] = "hx",
) -> None:
    import os
    import shutil
    import subprocess

    from stackops.utils.managed_files import ensure_managed_schema, get_managed_file_spec

    spec = get_managed_file_spec(which)
    file_path = spec.user_path if path is None else path.expanduser().resolve()
    if file_path.exists() and not file_path.is_file():
        _fail(f"Path exists but is not a file: {file_path}")
    editor_bin = shutil.which(editor)
    if editor_bin is None:
        _fail(f"Editor '{editor}' is not available on PATH.")

    if not file_path.exists():
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(spec.initial_content, encoding="utf-8")
            os.chmod(file_path, spec.file_mode)
            schema_path = ensure_managed_schema(spec=spec, data_path=file_path)
        except OSError as exc:
            _fail(f"Could not create {file_path}: {exc}")
        created_paths = str(file_path) if schema_path is None else f"{file_path} and {schema_path}"
        typer.echo(typer.style("✅ Created: ", fg=typer.colors.GREEN) + created_paths)

    result = subprocess.run([editor_bin, str(file_path)], check=False)
    if result.returncode != 0:
        _fail(f"Editor exited with status code {result.returncode}.")
