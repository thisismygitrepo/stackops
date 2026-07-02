import typer
from pathlib import Path
from typing import Annotated, Literal

from stackops.profile.dotfiles_mapper import ALL_OS_VALUES, DEFAULT_OS_FILTER
from stackops.profile.linking.options import CONFIG_FILE_SOURCE_LOOSE, CONFIG_FILE_SOURCE_MAP, CONFIG_SOURCE_LOOSE
from stackops.utils.cloud.encryption import EncryptionMode, EncryptionModeChoice, parse_encryption_mode


def sync(
    direction: Annotated[Literal["up", "u", "down", "d"], typer.Argument(..., help="'up'/'u' backs up; 'down'/'d' retrieves.")],
    cloud: Annotated[str | None, typer.Option("--cloud", "-c", help="☁ Cloud configuration name (rclone config name)")] = None,
    pwd: Annotated[
        str | None,
        typer.Option("--password", "-p", help="Symmetric GPG encryption password for entries with encryption: symmetric."),
    ] = None,
    which: Annotated[
        str | None, typer.Option("--which", "-w", help="📝 Comma-separated list of items to process (from mapper/data.yaml), or 'all' for all items")
    ] = None,
    source: Annotated[CONFIG_SOURCE_LOOSE, typer.Option("--source", "-s", help="📁 Which backup configuration to use: 'library', 'user', or 'all'")] = "all",
    use_link: Annotated[
        bool,
        typer.Option(
            "--use-link",
            "-l",
            help="🔗 On sync down, download from each entry's share_url with requests instead of rclone.",
        ),
    ] = False,
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
        main_backup_retrieve(direction=direction_resolved, which=which, cloud=cloud, source=source, use_link=use_link, pwd=pwd)
    except ValueError as exc:
        msg = typer.style("Error: ", fg=typer.colors.RED) + str(exc)
        typer.echo(msg)
        raise typer.Exit(code=1)


def _ordered_os_tokens(os_filter: str) -> list[str]:
    requested = {part.strip().lower() for part in os_filter.split(",") if part.strip()}
    return [value for value in ALL_OS_VALUES if value in requested]


def _default_data_entry_name(path_local: str, os_filter: str) -> str:
    from stackops.scripts.python.helpers.helpers_cloud.backup_registration import sanitize_entry_name

    base_name = sanitize_entry_name(Path(path_local).expanduser().stem)
    os_tokens = _ordered_os_tokens(os_filter)
    if len(os_tokens) == len(ALL_OS_VALUES):
        return base_name
    if len(os_tokens) == 0:
        return base_name
    return f"{base_name}_{'_'.join(os_tokens)}"


def _default_rel2home(path_local: str) -> bool:
    local_path = Path(path_local).expanduser().absolute()
    return local_path.is_relative_to(Path.home())


def _prompt_register_data_options(
    *,
    path_local: str | None,
    group: str,
    name: str | None,
    path_cloud: str | None,
    share_url: str | None,
    zip_: bool,
    encryption: EncryptionModeChoice | None,
    pwd: str | None,
    rel2home: bool | None,
    os: str,
) -> tuple[str, str, str, str, str | None, bool, EncryptionMode | None, bool, str]:
    from stackops.scripts.python.helpers.helpers_cloud.cloud_path_resolver import ES
    from stackops.scripts.python.helpers.helpers_devops.register_interactive import ask_bool, ask_choice, ask_text, confirm_summary

    path_default = path_local or Path.cwd().as_posix()
    prompted_path_local = ask_text(
        "Local path", help_text="Local file or directory to back up. The path must exist when the entry is written.", default=path_default
    )
    assert prompted_path_local is not None
    prompted_group = ask_text("Group", help_text="Top-level group in mapper/data.yaml.", default=group)
    prompted_os = ask_text("OS filter", help_text=f"Comma-separated OS list. Valid values are: {', '.join(ALL_OS_VALUES)}.", default=os)
    assert prompted_group is not None
    assert prompted_os is not None
    entry_name_default = name or _default_data_entry_name(path_local=prompted_path_local, os_filter=prompted_os)
    prompted_name = ask_text("Entry name", help_text="YAML key to use inside the selected backup group.", default=entry_name_default)
    prompted_path_cloud = ask_text(
        "Cloud path", help_text="Cloud object path. Use ^ to let StackOps derive the path from the local file or directory.", default=path_cloud or ES
    )
    prompted_share_url = ask_text(
        "Share URL",
        help_text="Optional http(s) share link used by `devops data sync down --use-link`. Leave blank for null.",
        default=share_url,
        allow_empty=True,
    )
    prompted_zip = ask_bool("Zip before upload", help_text="Store this entry as a zip archive before upload.", default=zip_)
    resolved_encryption = None if encryption is None else parse_encryption_mode(encryption, label="Encryption mode")
    encryption_default = "symmetric" if pwd is not None else resolved_encryption or "none"
    encryption_choice = ask_choice(
        "Encryption mode",
        help_text="Choose none for plaintext, asymmetric for configured GPG recipients, or symmetric for password-based GPG.",
        choices=("none", "asymmetric", "symmetric"),
        default=encryption_default,
    )
    match encryption_choice:
        case "none":
            prompted_encryption: EncryptionMode | None = None
        case "asymmetric":
            prompted_encryption = "asymmetric"
        case "symmetric":
            prompted_encryption = "symmetric"
        case _:
            raise RuntimeError(f"Unknown encryption choice: {encryption_choice}")
    rel2home_default = rel2home if rel2home is not None else _default_rel2home(prompted_path_local)
    prompted_rel2home = ask_bool(
        "Store relative to home",
        help_text="When enabled, paths under your home directory are stored as ~/... instead of absolute paths.",
        default=rel2home_default,
    )
    assert prompted_name is not None
    assert prompted_path_cloud is not None
    confirm_summary(
        "Data Register Review",
        [
            f"path_local: {prompted_path_local}",
            f"group: {prompted_group}",
            f"name: {prompted_name}",
            f"path_cloud: {prompted_path_cloud}",
            f"share_url: {prompted_share_url or 'null'}",
            f"zip: {prompted_zip}",
            f"encryption: {prompted_encryption or 'null'}",
            f"rel2home: {prompted_rel2home}",
            f"os: {prompted_os}",
        ],
    )
    return (
        prompted_path_local,
        prompted_group,
        prompted_name,
        prompted_path_cloud,
        prompted_share_url,
        prompted_zip,
        prompted_encryption,
        prompted_rel2home,
        prompted_os,
    )


def register_data(
    path_local: Annotated[str | None, typer.Argument(help="Local file/folder path to back up.")] = None,
    group: Annotated[str, typer.Option("--group", "-g", help="Group name in mapper/data.yaml.")] = "default",
    name: Annotated[str | None, typer.Option("--name", "-n", help="Entry name inside the group in mapper/data.yaml.")] = None,
    path_cloud: Annotated[str | None, typer.Option("--path-cloud", "-C", help="Cloud path override (optional).")] = None,
    share_url: Annotated[str | None, typer.Option("--share-url", "-u", help="Optional http(s) share URL for sync down --use-link.")] = None,
    zip_: Annotated[bool, typer.Option("--no-zip", "-z", help="Store the backup entry without zipping before upload.")] = True,
    encryption: Annotated[
        EncryptionModeChoice | None,
        typer.Option("--encryption", "-e", help="Encryption mode: symmetric/s or asymmetric/a. Omit for plaintext."),
    ] = None,
    pwd: Annotated[
        str | None, typer.Option("--password", "-p", help="Symmetric GPG encryption password. Requires --encryption symmetric and is not stored.")
    ] = None,
    rel2home: Annotated[bool | None, typer.Option("--no-rel2home", "-r", help="Store the local path as absolute even when it is under home.")] = None,
    os: Annotated[
        str, typer.Option("--os", "-o", help=f"OS filter for this backup entry. Comma-separated values from: {', '.join(ALL_OS_VALUES)}.")
    ] = DEFAULT_OS_FILTER,
    interactive: Annotated[bool, typer.Option("--interactive", "-i", help="Prompt for register fields one step at a time.")] = False,
) -> None:
    from stackops.scripts.python.helpers.helpers_cloud.backup_registration import register_backup_entry

    if interactive:
        path_local, group, name, path_cloud, share_url, zip_, encryption, rel2home, os = _prompt_register_data_options(
            path_local=path_local,
            group=group,
            name=name,
            path_cloud=path_cloud,
            share_url=share_url,
            zip_=zip_,
            encryption=encryption,
            pwd=pwd,
            rel2home=rel2home,
            os=os,
        )
    if path_local is None:
        typer.echo("Error: PATH_LOCAL is required unless --interactive is used.", err=True)
        raise typer.Exit(code=1)
    try:
        backup_path, entry_name, replaced = register_backup_entry(
            path_local=path_local,
            group=group,
            entry_name=name,
            path_cloud=path_cloud,
            share_url=share_url,
            zip_=zip_,
            encryption=encryption,
            password=pwd,
            rel2home=rel2home,
            os=os,
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
    source: Annotated[
        CONFIG_FILE_SOURCE_LOOSE,
        typer.Option("--source", "-s", help="📁 Which backup configuration file to edit: 'user' or 'library'."),
    ] = "user",
) -> None:
    import shutil
    import subprocess

    from stackops.scripts.python.helpers.helpers_cloud.backup_config import (
        LIBRARY_BACKUP_PATH,
        USER_BACKUP_PATH,
        DEFAULT_BACKUP_HEADER,
    )

    source_key = CONFIG_FILE_SOURCE_MAP[source]

    if source_key == "user":
        file_path = USER_BACKUP_PATH
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            if file_path.exists():
                if not file_path.is_file():
                    msg = typer.style("Error: ", fg=typer.colors.RED) + f"User backup path is not a file: {file_path}"
                    typer.echo(msg)
                    raise typer.Exit(code=1)
            else:
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
        if not file_path.is_file():
            msg = typer.style("Error: ", fg=typer.colors.RED) + f"Library backup path is not a file: {file_path}"
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
    from stackops.scripts.python.helpers.helpers_devops import cli_data_subset

    app = typer.Typer(
        name="data",
        help="🗄 <d> Backup and retrieve configuration files and directories to/from cloud storage.",
        no_args_is_help=True,
        add_help_option=True,
        add_completion=False,
    )

    app.command(name="sync", no_args_is_help=True, hidden=False, help="🔄 <s> Back up or retrieve files and directories using rclone or share links.")(
        sync
    )

    app.command(name="s", no_args_is_help=True, hidden=True)(sync)

    app.command(name="register", no_args_is_help=True, hidden=False, help="📝 <r> Register a new backup entry in user mapper/data.yaml.")(register_data)

    app.command(name="r", no_args_is_help=True, hidden=True)(register_data)

    app.command(name="subset", no_args_is_help=True, hidden=False, help=f"📦 <u> {cli_data_subset.DATA_SUBSET_HELP}")(cli_data_subset.subset)

    app.command(name="u", no_args_is_help=True, hidden=True)(cli_data_subset.subset)

    app.command(name="edit", no_args_is_help=False, hidden=False, help="✏️ <e> Open backup configuration file in nano, hx, or code.")(edit_data)

    app.command(name="e", no_args_is_help=False, hidden=True)(edit_data)

    return app
