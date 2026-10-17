import shutil
import subprocess
from pathlib import Path
from typing import Annotated, Literal

import typer


def edit_repositories(
    specs_path: Annotated[
        Path | None, typer.Option("--specs-path", "-s", help="Path to repos.json specification file.")
    ] = None,
    editor: Annotated[
        Literal["nano", "hx", "code"], typer.Option("--editor", "-e", help="Editor to open repos.json. Defaults to hx.")
    ] = "hx",
) -> None:
    from stackops.scripts.python.helpers.helpers_repos.spec_store import resolve_repos_spec_path
    from stackops.utils.managed_file_operations import initialize_managed_file, validate_managed_file
    from stackops.utils.managed_files import get_managed_file_spec

    try:
        spec_path = resolve_repos_spec_path(specs_path=specs_path)
        if spec_path.exists() and not spec_path.is_file():
            typer.echo(f"""❌ Specification path is not a file: {spec_path}""", err=True)
            raise typer.Exit(code=1)
        editor_bin = shutil.which(editor)
        if editor_bin is None:
            typer.echo(f"""❌ Editor '{editor}' is not available on PATH.""", err=True)
            raise typer.Exit(code=1)
        existed = spec_path.exists()
        initialize_managed_file(spec=get_managed_file_spec("repos"), data_path=spec_path)
        if not existed:
            typer.echo(f"""Created repository specification: {spec_path}""")
        editor_command = [editor_bin, "--wait"] if editor == "code" else [editor_bin]
        editor_command.append(spec_path.as_posix())
        typer.echo(f"""📝 Editing repository specification: {spec_path}""")
        result = subprocess.run(editor_command, check=False)
    except OSError as error:
        typer.echo(f"""❌ Could not edit repository specification: {error}""", err=True)
        raise typer.Exit(code=1) from error
    if result.returncode != 0:
        typer.echo(f"""❌ Editor exited with status code {result.returncode}.""", err=True)
        raise typer.Exit(code=result.returncode if result.returncode > 0 else 1)
    try:
        validate_managed_file(kind="repos", data_path=spec_path)
    except (ValueError, OSError) as error:
        typer.echo(f"""❌ Invalid repository specification after editing: {error}""", err=True)
        raise typer.Exit(code=1) from error
    typer.echo(f"""✅ Repository specification validated: {spec_path}""")
