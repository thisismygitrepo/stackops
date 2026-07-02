from pathlib import Path
from typing import NoReturn

import typer

from stackops.scripts.python.helpers.helpers_cloud.backup_config import (
    BackupConfig,
    load_backup_config_file,
    serialize_backup_config,
)
from stackops.scripts.python.helpers.helpers_devops.cli_subset_support import SubsetOutputConflictAction


def load_existing_subset_output(
    *,
    source_path: Path,
    output_path: Path,
    on_conflict: SubsetOutputConflictAction,
) -> BackupConfig | None:
    _reject_source_output_identity(source_path=source_path, output_path=output_path)
    if output_path.is_symlink():
        _fail(f"Subset output path must not be a symbolic link: {output_path}")
    if output_path.exists() and not output_path.is_file():
        _fail(f"Subset output path is not a file: {output_path}")
    if on_conflict == "throw-error":
        if output_path.exists():
            _fail(
                f"Subset output file already exists: {output_path}. "
                + "Pass --on-conflict append to add entries or --on-conflict overwrite to replace it."
            )
        return None
    if on_conflict == "overwrite":
        return None
    if not output_path.exists():
        _fail(f"Subset output file does not exist: {output_path}. Use --on-conflict throw-error to create a new output file.")
    try:
        existing_config = load_backup_config_file(output_path, empty_as_config=True)
    except ValueError as exc:
        _fail(f"Cannot append to invalid subset output file {output_path}: {exc}")
    if existing_config is None:
        _fail(f"Cannot append to invalid subset output file: {output_path}")
    return existing_config


def write_subset_output(
    *,
    source_path: Path,
    output_path: Path,
    output_config: BackupConfig,
    on_conflict: SubsetOutputConflictAction,
) -> None:
    _reject_source_output_identity(source_path=source_path, output_path=output_path)
    serialized_config = serialize_backup_config(output_config)
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if on_conflict == "throw-error":
            with output_path.open("x", encoding="utf-8") as output_file:
                output_file.write(serialized_config)
            return
        if output_path.is_symlink():
            _fail(f"Subset output path must not be a symbolic link: {output_path}")
        if on_conflict == "append" and (not output_path.exists() or not output_path.is_file()):
            _fail(f"Subset output file disappeared or changed before it could be updated: {output_path}")
        output_path.write_text(serialized_config, encoding="utf-8")
    except FileExistsError:
        _fail(f"Subset output file was created while entries were being selected: {output_path}")
    except OSError as exc:
        _fail(f"Could not write subset output file {output_path}: {exc}")


def _reject_source_output_identity(*, source_path: Path, output_path: Path) -> None:
    if source_path.resolve(strict=False) == output_path.resolve(strict=False):
        _fail("Subset output path must be different from the source backup configuration file.")
    if not output_path.exists():
        return
    try:
        paths_share_file = source_path.samefile(output_path)
    except OSError as exc:
        _fail(f"Could not compare source and output paths: {exc}")
    if paths_share_file:
        _fail("Subset output path must not refer to the source backup configuration file.")


def _fail(message: str) -> NoReturn:
    typer.echo(typer.style("Error: ", fg=typer.colors.RED) + message)
    raise typer.Exit(code=1)
