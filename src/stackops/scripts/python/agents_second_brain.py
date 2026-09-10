from datetime import date
from importlib.resources import files
from pathlib import Path
from typing import Annotated

import typer

from stackops.scripts.python.helpers.helpers_agents.agents_second_brain_activity import read_second_brain_git_activity
from stackops.scripts.python.helpers.helpers_agents.agents_second_brain_records import (
    align_second_brain_updates,
    read_second_brain_updates,
)
from stackops.scripts.python.helpers.helpers_agents.agents_second_brain_report import (
    show_second_brain_align_result,
    show_second_brain_status,
)


def configure_second_brain(*, home: Path, instructions_text: str) -> Path:
    second_brain_path = home.joinpath("code", "agents", "second-brain")
    instructions_path = second_brain_path.joinpath("AGENTS.md")

    second_brain_path.mkdir(parents=True, exist_ok=True)
    if instructions_path.is_dir():
        raise IsADirectoryError(f"Refusing to replace Second Brain instructions directory: {instructions_path}")
    if not instructions_path.exists():
        instructions_path.write_text(instructions_text, encoding="utf-8")
    return instructions_path


def config() -> None:
    home = Path.home()
    instructions_text = files("stackops.scripts.python").joinpath("agents_second_brain.instructions.md").read_text(encoding="utf-8")
    instructions_path = configure_second_brain(home=home, instructions_text=instructions_text)

    typer.echo(f"Second Brain instructions: {instructions_path}")


def status() -> None:
    second_brain_root = Path.home().joinpath("code", "agents", "second-brain")
    today = date.today()
    try:
        update_files = read_second_brain_updates(second_brain_root=second_brain_root)
        git_activity = read_second_brain_git_activity(second_brain_root=second_brain_root, today=today)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except (OSError, RuntimeError) as error:
        typer.echo(f"""Could not read Second Brain status: {error}""", err=True)
        raise typer.Exit(code=1) from error

    show_second_brain_status(second_brain_root=second_brain_root, update_files=update_files, git_activity=git_activity, today=today)


def align(
    force: Annotated[bool, typer.Option("--force", "-f", help="Authorize deletion of invalid updates. Otherwise, preview only.")] = False,
) -> None:
    second_brain_root = Path.home().joinpath("code", "agents", "second-brain")
    try:
        update_files = read_second_brain_updates(second_brain_root=second_brain_root)
        removed_rows = align_second_brain_updates(update_files=update_files, force=force)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except OSError as error:
        typer.echo(f"""Could not align Second Brain updates: {error}""", err=True)
        raise typer.Exit(code=1) from error

    show_second_brain_align_result(
        second_brain_root=second_brain_root,
        removed_rows=removed_rows,
        scanned_file_count=len(update_files),
        force=force,
    )


def get_app() -> typer.Typer:
    second_brain_app = typer.Typer(help="Second Brain commands", no_args_is_help=True, add_help_option=True, add_completion=False)
    second_brain_app.command(name="config", no_args_is_help=False, short_help="<c> Configure the Second Brain repository")(config)
    second_brain_app.command(name="c", no_args_is_help=False, hidden=True)(config)
    second_brain_app.command(name="status", no_args_is_help=False, short_help="<s> Show Second Brain statistics and invalid updates")(status)
    second_brain_app.command(name="s", no_args_is_help=False, hidden=True)(status)
    second_brain_app.command(name="align", no_args_is_help=False, short_help="<a> Preview invalid updates; --force deletes them")(align)
    second_brain_app.command(name="a", no_args_is_help=False, hidden=True)(align)
    return second_brain_app
