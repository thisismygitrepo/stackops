from pathlib import Path

import typer


def config() -> None:
    link_path = Path.home().joinpath("code", "agents", "second-brain")
    target_path = Path.home().joinpath("dotfiles", "stackops", "second-brain")
    link_path.parent.mkdir(parents=True, exist_ok=True)
    link_path.symlink_to(target_path, target_is_directory=True)
    typer.echo(f"Created symlink: {link_path} -> {target_path}")


def get_app() -> typer.Typer:
    second_brain_app = typer.Typer(
        help="Second Brain commands",
        no_args_is_help=True,
        add_help_option=True,
        add_completion=False,
    )
    second_brain_app.command(name="config", short_help="Link the Second Brain configuration")(config)
    return second_brain_app
