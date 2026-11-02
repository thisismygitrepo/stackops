import json
from pathlib import Path
from typing import Literal

import typer

from stackops.utils.managed_files import ManagedFileKind


def run_managed_file_action(*, kind: ManagedFileKind, action: Literal["path", "init", "validate"], path: Path | None) -> None:
    from stackops.utils.managed_file_operations import describe_managed_file, initialize_managed_file, validate_managed_file
    from stackops.utils.managed_files import resolve_managed_file

    try:
        spec, data_path = resolve_managed_file(kind=kind, path=path)
        match action:
            case "path":
                typer.echo(json.dumps(describe_managed_file(spec=spec, data_path=data_path), indent=2))
            case "init":
                initialize_managed_file(spec=spec, data_path=data_path)
                typer.echo(json.dumps(describe_managed_file(spec=spec, data_path=data_path), indent=2))
            case "validate":
                validate_managed_file(kind=kind, data_path=data_path)
                typer.echo(f"""Valid {kind} file: {data_path}""")
    except (OSError, ValueError) as error:
        typer.echo(f"""Error: {error}""", err=True)
        raise typer.Exit(code=1) from error


def run_managed_file_edit(*, kind: ManagedFileKind, path: Path | None, editor: Literal["hx", "nano", "code"]) -> None:
    from stackops.utils.file_editor_cli import resolve_editor_command, run_file_editor
    from stackops.utils.managed_file_operations import initialize_managed_file, validate_managed_file
    from stackops.utils.managed_files import resolve_managed_file

    try:
        spec, data_path = resolve_managed_file(kind=kind, path=path)
        existed = data_path.exists()
        if existed and not data_path.is_file():
            raise ValueError(f"""Configuration path is not a file: {data_path}""")
        editor_command = resolve_editor_command(editor=editor)
        initialize_managed_file(spec=spec, data_path=data_path)
        if not existed:
            typer.echo(f"""Created {kind} file: {data_path}""")
    except (OSError, ValueError) as error:
        typer.echo(f"""Error: {error}""", err=True)
        raise typer.Exit(code=1) from error

    typer.echo(f"""Editing {kind} file: {data_path}""")
    run_file_editor(path=data_path, command=editor_command)
    try:
        validate_managed_file(kind=kind, data_path=data_path)
    except (OSError, ValueError) as error:
        typer.echo(f"""Error: Invalid {kind} file after editing: {error}""", err=True)
        raise typer.Exit(code=1) from error
    typer.echo(f"""Validated: {data_path}""")
