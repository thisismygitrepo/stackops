import shutil
import subprocess
from pathlib import Path
from typing import Literal

import typer


def resolve_editor_command(*, editor: Literal["hx", "nano", "code"]) -> list[str]:
    from stackops.utils.cli_utils.interaction import require_interactive

    require_interactive("Opening an editor; use path/init/validate commands for file-based automation")
    editor_bin = shutil.which(editor)
    if editor_bin is None:
        typer.echo(f"""Editor '{editor}' is not available on PATH.""", err=True)
        raise typer.Exit(code=1)
    return [editor_bin, "--wait"] if editor == "code" else [editor_bin]


def run_file_editor(*, path: Path, command: list[str]) -> None:
    from stackops.utils.cli_utils.interaction import require_interactive

    require_interactive("Opening an editor")
    try:
        result = subprocess.run([*command, str(path)], check=False)
    except OSError as error:
        typer.echo(f"""Could not edit {path}: {error}""", err=True)
        raise typer.Exit(code=1) from error
    if result.returncode != 0:
        typer.echo(f"""Editor exited with status code {result.returncode}.""", err=True)
        raise typer.Exit(code=result.returncode if result.returncode > 0 else 1)
