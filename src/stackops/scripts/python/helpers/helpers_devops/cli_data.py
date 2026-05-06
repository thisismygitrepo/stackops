import typer
import shutil
import subprocess
from typing import Annotated, Literal, assert_never

from stackops.profile.dotfiles_mapper import ALL_OS_VALUES, DEFAULT_OS_FILTER
from stackops.profile.create_links_export import REPO_LOOSE


def sync(
    direction: Annotated[Literal["up", "u", "down", "d"], typer.Argument(..., help="'up'/'u' backs up; 'down'/'d' retrieves.")],
    cloud: Annotated[str | None, typer.Option("--cloud", "-c", help="☁ Cloud configuration name (rclone config name)")] = None,
    which: Annotated[
        str | None, typer.Option("--which", "-w", help="📝 Comma-separated list of items to process (from mapper_data.yaml), or 'all' for all items")
    ] = None,
    repo: Annotated[REPO_LOOSE, typer.Option("--repo", "-r", help="📁 Which backup configuration to use: 'library', 'user', or 'all'")] = "all",
    # interactive: Annotated[bool, typer.Option("--interactive", "-i", help="🤔 Prompt the selection of which items to process")] = False,
) -> None:
    from stackops.scripts.python.helpers.helpers_devops.cli_backup_retrieve import main_backup_retrieve
    match direction:
        case "up" | "u":
            direction_resolved: Literal["BACKUP", "RETRIEVE"] = "BACKUP"
        case "down" | "d":
            direction_resolved = "RETRIEVE"
        case _:
            typer.echo("Error: Invalid direction. Use 'up' or 'down'.")
            raise typer.Exit(code=1)
    try:
        main_backup_retrieve(direction=direction_resolved, which=which, cloud=cloud, repo=repo)
    except ValueError as exc:
        msg = typer.style("Error: ", fg=typer.colors.RED) + str(exc)
        typer.echo(msg)
        raise typer.Exit(code=1)


def register_data(
    path_local: Annotated[str, typer.Argument(..., help="Local file/folder path to back up.")],
    group: Annotated[str, typer.Option("--group", "-g", help="Group name in mapper_data.yaml.")] = "default",
    name: Annotated[str | None, typer.Option("--name", "-n", help="Entry name inside the group in mapper_data.yaml.")] = None,
    path_cloud: Annotated[str | None, typer.Option("--path-cloud", "-C", help="Cloud path override (optional).")] = None,
    zip_: Annotated[bool, typer.Option("--zip/--no-zip", "-z/-nz", help="Zip before uploading.")] = True,
    encrypt: Annotated[bool, typer.Option("--encrypt/--no-encrypt", "-e/-ne", help="Encrypt before uploading.")] = True,
    rel2home: Annotated[bool | None, typer.Option("--rel2home/--no-rel2home", "-r/-nr", help="Treat the local path as relative to home.")] = None,
    os: Annotated[str, typer.Option("--os", "-o", help=f"OS filter for this backup entry. Comma-separated values from: {', '.join(ALL_OS_VALUES)}.")] = DEFAULT_OS_FILTER,
) -> None:
    from stackops.scripts.python.helpers.helpers_devops.cli_backup_retrieve import register_backup_entry

    try:
        backup_path, entry_name, replaced = register_backup_entry(
            path_local=path_local, group=group, entry_name=name, path_cloud=path_cloud, zip_=zip_, encrypt=encrypt, rel2home=rel2home, os=os
        )
    except ValueError as exc:
        msg = typer.style("Error: ", fg=typer.colors.RED) + str(exc)
        typer.echo(msg)
        raise typer.Exit(code=1)
    action = "Updated" if replaced else "Added"
    typer.echo(f"{action} backup entry '{entry_name}' in {backup_path}")


def edit_data(
    editor: Annotated[
        Literal["nano", "hx", "code"],
        typer.Option("--editor", "-e", help="📝 Editor to open the backup config file."),
    ] = "hx",
    repo: Annotated[
        Literal["library", "l", "user", "u"],
        typer.Option("--repo", "-r", help="📁 Which backup configuration file to edit: 'user' or 'library'."),
    ] = "user",
) -> None:
    from stackops.scripts.python.helpers.helpers_devops.backup_config import (
        LIBRARY_BACKUP_PATH,
        USER_BACKUP_PATH,
        DEFAULT_BACKUP_HEADER,
    )

    repo_key: Literal["library", "user"]
    match repo:
        case "library" | "l":
            repo_key = "library"
        case "user" | "u":
            repo_key = "user"
        case _:
            assert_never(repo)

    if repo_key == "user":
        file_path = USER_BACKUP_PATH
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            if not file_path.exists():
                file_path.write_text(DEFAULT_BACKUP_HEADER, encoding="utf-8")
        except OSError as exc:
            msg = typer.style("Error: ", fg=typer.colors.RED) + f"Could not prepare user backup file {file_path}: {exc}"
            typer.echo(msg)
            raise typer.Exit(code=1) from exc
    else:
        file_path = LIBRARY_BACKUP_PATH
        if not file_path.exists():
            msg = typer.style("Error: ", fg=typer.colors.RED) + f"Library backup file not found: {file_path}"
            typer.echo(msg)
            raise typer.Exit(code=1)

    editor_bin = shutil.which(editor)
    if editor_bin is None:
        msg = typer.style("Error: ", fg=typer.colors.RED) + f"Editor '{editor}' is not available on PATH."
        typer.echo(msg)
        raise typer.Exit(code=1)

    try:
        result = subprocess.run([editor_bin, str(file_path)], check=False)
    except OSError as exc:
        msg = typer.style("Error: ", fg=typer.colors.RED) + f"Could not start editor '{editor}': {exc}"
        typer.echo(msg)
        raise typer.Exit(code=1) from exc

    if result.returncode != 0:
        msg = typer.style("Error: ", fg=typer.colors.RED) + f"Editor exited with status code {result.returncode}."
        typer.echo(msg)
        raise typer.Exit(code=result.returncode if result.returncode > 0 else 1)


def get_app() -> typer.Typer:
    app = typer.Typer(
        name="data",
        help="🗄 <d> Backup and retrieve configuration files and directories to/from cloud storage using rclone.",
        no_args_is_help=True,
        add_help_option=True,
        add_completion=False,
    )

    app.command(name="sync", no_args_is_help=True, hidden=False, help="🔄 <s> Back up or retrieve files and directories using rclone.")(
        sync
    )

    app.command(name="s", no_args_is_help=True, hidden=True)(sync)

    app.command(name="register", no_args_is_help=True, hidden=False, help="📝 <r> Register a new backup entry in user mapper_data.yaml.")(register_data)

    app.command(name="r", no_args_is_help=True, hidden=True)(register_data)

    app.command(name="edit", no_args_is_help=False, hidden=False, help="✏️ <e> Open backup configuration file in nano, hx, or code.")(edit_data)

    app.command(name="e", no_args_is_help=False, hidden=True)(edit_data)

    return app
