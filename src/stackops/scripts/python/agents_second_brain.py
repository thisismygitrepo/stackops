from importlib.resources import files
from pathlib import Path

import typer


def configure_second_brain(*, home: Path, instructions_text: str) -> tuple[Path, Path, Path]:
    link_path = home.joinpath("code", "agents", "second-brain")
    target_path = home.joinpath("dotfiles", "stackops", "second-brain")
    instructions_path = target_path.joinpath("AGENTS.md")

    link_exists = link_path.exists() or link_path.is_symlink()
    link_is_current = link_path.is_symlink() and link_path.readlink() == target_path
    instructions_exist = instructions_path.exists() or instructions_path.is_symlink()
    if link_exists and not link_is_current:
        if link_path.is_dir() and not link_path.is_symlink():
            raise IsADirectoryError(f"Refusing to replace Second Brain directory: {link_path}")
        raise FileExistsError(f"Refusing to replace Second Brain configuration path: {link_path}")
    if instructions_path.is_dir() and not instructions_path.is_symlink():
        raise IsADirectoryError(f"Refusing to replace Second Brain instructions directory: {instructions_path}")

    link_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.mkdir(parents=True, exist_ok=True)
    if not instructions_exist:
        instructions_path.write_text(instructions_text, encoding="utf-8")
    if not link_is_current:
        link_path.symlink_to(target_path, target_is_directory=True)
    return instructions_path, link_path, target_path


def config() -> None:
    home = Path.home()
    instructions_text = files("stackops.scripts.python").joinpath("agents_second_brain.instructions.md").read_text(encoding="utf-8")
    instructions_path, link_path, target_path = configure_second_brain(home=home, instructions_text=instructions_text)

    typer.echo(f"Second Brain instructions: {instructions_path}")
    typer.echo(f"Configured symlink: {link_path} -> {target_path}")


def get_app() -> typer.Typer:
    second_brain_app = typer.Typer(help="Second Brain commands", no_args_is_help=True, add_help_option=True, add_completion=False)
    second_brain_app.command(name="config", short_help="Link the Second Brain configuration")(config)
    return second_brain_app
