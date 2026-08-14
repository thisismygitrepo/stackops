from importlib.resources import files
from pathlib import Path

import typer


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


def get_app() -> typer.Typer:
    second_brain_app = typer.Typer(help="Second Brain commands", no_args_is_help=True, add_help_option=True, add_completion=False)
    second_brain_app.command(name="config", no_args_is_help=False, short_help="<c> Configure the Second Brain repository")(config)
    second_brain_app.command(name="c", no_args_is_help=False, hidden=True)(config)
    return second_brain_app
