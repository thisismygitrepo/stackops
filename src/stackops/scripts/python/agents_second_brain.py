from importlib.resources import files
from pathlib import Path
from typing import Annotated

import typer


def config(overwrite: Annotated[bool, typer.Option("--overwrite", "-w", help="Replace existing Second Brain configuration files.")] = False) -> None:
    link_path = Path.home().joinpath("code", "agents", "second-brain")
    target_path = Path.home().joinpath("dotfiles", "stackops", "second-brain")
    instructions_path = target_path.joinpath("AGENTS.md")
    instructions_text = files("stackops.scripts.python").joinpath("agents_second_brain.instructions.md").read_text(encoding="utf-8")

    link_exists = link_path.exists() or link_path.is_symlink()
    link_is_current = link_path.is_symlink() and link_path.readlink() == target_path
    instructions_exist = instructions_path.exists() or instructions_path.is_symlink()
    if link_exists and not link_is_current and not overwrite:
        raise FileExistsError(f"Second Brain configuration path already exists: {link_path}")
    if instructions_exist and not overwrite:
        raise FileExistsError(f"Second Brain instructions already exist: {instructions_path}")
    if link_exists and not link_is_current and link_path.is_dir() and not link_path.is_symlink():
        raise IsADirectoryError(f"Refusing to overwrite Second Brain directory: {link_path}")
    if instructions_path.is_dir() and not instructions_path.is_symlink():
        raise IsADirectoryError(f"Refusing to overwrite Second Brain instructions directory: {instructions_path}")

    link_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.mkdir(parents=True, exist_ok=True)
    if link_exists and not link_is_current:
        link_path.unlink()
    if instructions_path.is_symlink():
        instructions_path.unlink()
    instructions_path.write_text(instructions_text, encoding="utf-8")
    if not link_is_current:
        link_path.symlink_to(target_path, target_is_directory=True)

    typer.echo(f"Installed Second Brain instructions: {instructions_path}")
    typer.echo(f"Configured symlink: {link_path} -> {target_path}")


def get_app() -> typer.Typer:
    second_brain_app = typer.Typer(help="Second Brain commands", no_args_is_help=True, add_help_option=True, add_completion=False)
    second_brain_app.command(name="config", short_help="Link the Second Brain configuration")(config)
    return second_brain_app
