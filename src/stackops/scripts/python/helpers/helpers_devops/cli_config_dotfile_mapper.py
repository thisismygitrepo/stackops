"""Dotfile mapper registration commands."""

import hashlib
from pathlib import Path
import shutil
import subprocess
from typing import Annotated, Literal, cast

import typer

from stackops.profile.dotfiles_mapper import (
    DEFAULT_DOTFILE_MAPPER_HEADER,
    DEFAULT_OS_FILTER,
    LIBRARY_MAPPER_PATH,
    USER_MAPPER_PATH,
    RawMapperEntry,
    dump_dotfiles_mapper,
    load_dotfiles_mapper,
    normalize_os_filter,
    write_dotfiles_mapper,
)
from stackops.profile.link_options import (
    CONFIG_FILE_SOURCE_LOOSE,
    CONFIG_FILE_SOURCE_MAP,
    METHOD_LOOSE,
    METHOD_MAP,
)
from stackops.utils.link_conflict import (
    ON_CONFLICT_LOOSE,
    ON_CONFLICT_MAPPER,
)
from stackops.utils.source_of_truth import CONFIG_ROOT, DOTFILES_MAPPER_FILES_ROOT, DOTFILES_ROOT

BACKUP_ROOT_FLAT = DOTFILES_MAPPER_FILES_ROOT
FLAT_PATH_HASH_LENGTH = 16


def _format_home_relative_path(path: Path) -> str:
    home = Path.home()
    if path.is_relative_to(home):
        return f"~/{path.relative_to(home).as_posix()}"
    return path.as_posix()


def _format_self_managed_mapper_path(path: Path) -> str:
    config_root = Path(CONFIG_ROOT).expanduser().resolve()
    dotfiles_root = Path(DOTFILES_ROOT).expanduser().resolve()
    resolved_path = path.expanduser().resolve(strict=False)
    if resolved_path == config_root:
        return "CONFIG_ROOT"
    if resolved_path.is_relative_to(config_root):
        relative_path = resolved_path.relative_to(config_root)
        return f"CONFIG_ROOT/{relative_path.as_posix()}"
    if resolved_path == dotfiles_root:
        return "DOTFILES_ROOT"
    if resolved_path.is_relative_to(dotfiles_root):
        relative_path = resolved_path.relative_to(dotfiles_root)
        return f"DOTFILES_ROOT/{relative_path.as_posix()}"
    return _format_home_relative_path(path)


def _build_entry_name(original_path: Path) -> str:
    return original_path.stem.replace(".", "_").replace("-", "_")


def _resolve_entry_name(original_path: Path, entry_name: str | None) -> str:
    if entry_name is None or not entry_name.strip():
        return _build_entry_name(original_path)
    return entry_name.strip()


def _build_flat_backup_name(original_path: Path) -> str:
    normalized_path = original_path.expanduser().absolute()
    location = _format_home_relative_path(normalized_path.parent)
    location_hash = hashlib.sha256(location.encode("utf-8")).hexdigest()[:FLAT_PATH_HASH_LENGTH]
    return f"{location_hash}.{normalized_path.name}"


def _build_mapper_entry(
    original_path: Path,
    self_managed_path: Path,
    method: Literal["symlink", "copy"],
    is_contents: bool,
    os_filter: str,
) -> RawMapperEntry:
    entry: RawMapperEntry = {
        "original": _format_home_relative_path(original_path),
        "self_managed": _format_self_managed_mapper_path(self_managed_path),
        "os": normalize_os_filter(os_filter),
    }
    if is_contents:
        entry["contents"] = True
    if method == "copy":
        entry["copy"] = True
    return entry


def _build_mapper_preview(section: str, entry_name: str, entry: RawMapperEntry) -> str:
    preview = dump_dotfiles_mapper(
        mapper={section: {entry_name: entry}},
        header="",
    )
    return preview.rstrip()


def _path_exists_for_register(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def _write_to_user_mapper(
    section: str,
    entry_name: str,
    original_path: Path,
    self_managed_path: Path,
    method: Literal["symlink", "copy"],
    is_contents: bool,
    os_filter: str,
) -> tuple[Path, RawMapperEntry]:
    mapper_path = USER_MAPPER_PATH
    mapper_path.parent.mkdir(parents=True, exist_ok=True)
    mapper = load_dotfiles_mapper(mapper_path) if mapper_path.exists() else {}
    section_entries = dict(mapper.get(section, {}))
    entry = _build_mapper_entry(
        original_path=original_path,
        self_managed_path=self_managed_path,
        method=method,
        is_contents=is_contents,
        os_filter=os_filter,
    )
    section_entries[entry_name] = entry
    mapper[section] = section_entries
    write_dotfiles_mapper(
        path=mapper_path,
        mapper=mapper,
        header=DEFAULT_DOTFILE_MAPPER_HEADER,
    )
    return mapper_path, entry


def record_mapping(orig_path: Path, new_path: Path, method: METHOD_LOOSE, section: str, os_filter: str, entry_name: str | None = None) -> None:
    resolved_entry_name = _resolve_entry_name(orig_path, entry_name)
    method_resolved = METHOD_MAP[method]
    mapper_file, entry = _write_to_user_mapper(
        section=section,
        entry_name=resolved_entry_name,
        original_path=orig_path,
        self_managed_path=new_path,
        method=method_resolved,
        is_contents=False,
        os_filter=os_filter,
    )
    preview = _build_mapper_preview(section=section, entry_name=resolved_entry_name, entry=entry)
    from rich.console import Console
    from rich.panel import Panel

    console = Console()
    console.print(
        Panel(
            f"📝 Mapping recorded in: [cyan]{mapper_file}[/cyan]\n\n{preview}",
            title="Mapper Entry Saved",
            border_style="cyan",
            padding=(1, 2),
        )
    )


def get_backup_path(orig_path: Path, sensitivity: Literal["private", "v", "public", "b"], destination: str | None, shared: bool) -> Path:
    match sensitivity:
        case "private" | "v" | "public" | "b":
            pass
        case _:
            raise ValueError(f"Unknown sensitivity: {sensitivity}")
    if destination is None:
        new_path = BACKUP_ROOT_FLAT.joinpath(_build_flat_backup_name(orig_path))
    else:
        if shared:
            dest_path = Path(destination).expanduser().absolute()
            new_path = dest_path.joinpath("shared").joinpath(orig_path.name)
        else:
            dest_path = Path(destination).expanduser().absolute()
            new_path = dest_path.joinpath(orig_path.name)
    return new_path


def get_original_path_from_backup_path(
    backup_path: Path, sensitivity: Literal["private", "v", "public", "b"], destination: str | None, shared: bool
) -> Path:
    match sensitivity:
        case "private" | "v" | "public" | "b":
            pass
        case _:
            raise ValueError(f"Unknown sensitivity: {sensitivity}")
    if destination is None:
        raise ValueError("Cannot derive the original path from a flat hashed backup path. Use the mapper entry instead.")
    else:
        dest_path = Path(destination).expanduser().absolute()
        if shared:
            relative_part = backup_path.relative_to(dest_path.joinpath("shared"))
        else:
            relative_part = backup_path.relative_to(dest_path)
        original_path = Path.home().joinpath(relative_part)
    return original_path


def _prompt_register_dotfile_options(
    *,
    file: str | None,
    method: METHOD_LOOSE,
    on_conflict: ON_CONFLICT_LOOSE,
    sensitivity: Literal["private", "v", "public", "b"],
    destination: str | None,
    section: str,
    os_filter: str,
    shared: bool,
    record: bool,
    entry_name: str | None,
) -> tuple[str, METHOD_LOOSE, ON_CONFLICT_LOOSE, Literal["private", "public"], str | None, str, str, bool, bool, str]:
    from stackops.scripts.python.helpers.helpers_devops.register_interactive import ask_bool, ask_choice, ask_text, confirm_summary

    file_default = file or Path.cwd().as_posix()
    prompted_file = ask_text(
        "File or directory",
        help_text="Local config file or directory to register. The original path or target self-managed path must exist.",
        default=file_default,
    )
    assert prompted_file is not None
    orig_path = Path(prompted_file).expanduser().absolute()
    method_default = METHOD_MAP[method]
    prompted_method = cast(
        METHOD_LOOSE,
        ask_choice(
            "Method",
            help_text="Use copy to keep separate files, or symlink to point the original path at the self-managed copy.",
            choices=("copy", "symlink"),
            default=method_default,
        ),
    )
    conflict_default = ON_CONFLICT_MAPPER[on_conflict]
    prompted_on_conflict = cast(
        ON_CONFLICT_LOOSE,
        ask_choice(
            "Conflict behavior",
            help_text="What to do if both the original path and self-managed path already exist.",
            choices=("throw-error", "overwrite-self-managed", "backup-self-managed", "overwrite-default-path", "backup-default-path"),
            default=conflict_default,
        ),
    )
    sensitivity_default = "private" if sensitivity in ("private", "v") else "public"
    prompted_sensitivity = cast(
        Literal["private", "public"],
        ask_choice(
            "Sensitivity",
            help_text="Private entries go into your private dotfiles area. Public entries go into the public/shared area.",
            choices=("private", "public"),
            default=sensitivity_default,
        ),
    )
    prompted_destination = ask_text(
        "Destination directory",
        help_text="Optional self-managed destination root. Leave blank to use the default flat dotfiles storage.",
        default=destination,
        allow_empty=True,
    )
    prompted_shared = ask_bool(
        "Shared destination", help_text="When a destination directory is provided, place the file under a shared subdirectory.", default=shared
    )
    default_entry_name = entry_name or _build_entry_name(orig_path)
    prompted_entry_name = ask_text("Mapper entry name", help_text="YAML key to use inside the selected mapper section.", default=default_entry_name)
    prompted_section = ask_text(
        "Mapper section", help_text="Top-level section in mapper/dotfiles.yaml where this entry should be recorded.", default=section
    )
    prompted_os_filter = ask_text("OS filter", help_text="Comma-separated OS list. Valid values are linux, darwin, and windows.", default=os_filter)
    prompted_record = ask_bool(
        "Record in mapper", help_text="Write the YAML entry to your user mapper. If disabled, StackOps prints a preview instead.", default=record
    )
    assert prompted_entry_name is not None
    assert prompted_section is not None
    assert prompted_os_filter is not None
    self_managed_path = get_backup_path(
        orig_path=orig_path, sensitivity=prompted_sensitivity, destination=prompted_destination, shared=prompted_shared
    )
    confirm_summary(
        "Config Register Review",
        [
            f"file: {prompted_file}",
            f"self_managed: {self_managed_path}",
            f"method: {prompted_method}",
            f"on_conflict: {prompted_on_conflict}",
            f"sensitivity: {prompted_sensitivity}",
            f"destination: {prompted_destination or '(default)'}",
            f"shared: {prompted_shared}",
            f"record: {prompted_record}",
            f"section: {prompted_section}",
            f"name: {prompted_entry_name}",
            f"os: {prompted_os_filter}",
        ],
    )
    return (
        prompted_file,
        prompted_method,
        prompted_on_conflict,
        prompted_sensitivity,
        prompted_destination,
        prompted_section,
        prompted_os_filter,
        prompted_shared,
        prompted_record,
        prompted_entry_name,
    )


def register_dotfile(
    file: Annotated[str | None, typer.Argument(help="file/folder path.")] = None,
    method: Annotated[METHOD_LOOSE, typer.Option(..., "--method", "-m", help="Method to use for linking files")] = "copy",
    on_conflict: Annotated[ON_CONFLICT_LOOSE, typer.Option(..., "--on-conflict", "-c", help="Action to take on conflict")] = "throw-error",
    sensitivity: Annotated[
        Literal["private", "v", "public", "b"], typer.Option(..., "--sensitivity", "-s", help="Sensitivity of the config file.")
    ] = "private",
    destination: Annotated[
        str | None, typer.Option("--destination", "-d", help="destination folder (override the default, use at your own risk)")
    ] = None,
    name: Annotated[str | None, typer.Option("--name", "-n", help="Entry name in mapper/dotfiles.yaml. Defaults to the file stem.")] = None,
    section: Annotated[str, typer.Option("--section", "-S", help="Section name in mapper/dotfiles.yaml to record this mapping.")] = "default",
    os_filter: Annotated[str, typer.Option("--os", "-o", help="Comma-separated OS list from: linux,darwin,windows.")] = DEFAULT_OS_FILTER,
    shared: Annotated[bool, typer.Option("--shared", "-h", help="Whether the config file is shared across destinations directory.")] = False,
    record: Annotated[bool, typer.Option("--record", "-r", help="Record the mapping in user's mapper.yaml")] = True,
    interactive: Annotated[bool, typer.Option("--interactive", "-i", help="Prompt for register fields one step at a time.")] = False,
) -> None:
    from rich.console import Console
    from rich.panel import Panel
    from stackops.utils.links import symlink_map, copy_map

    console = Console()
    if interactive:
        file, method, on_conflict, sensitivity, destination, section, os_filter, shared, record, name = _prompt_register_dotfile_options(
            file=file,
            method=method,
            on_conflict=on_conflict,
            sensitivity=sensitivity,
            destination=destination,
            section=section,
            os_filter=os_filter,
            shared=shared,
            record=record,
            entry_name=name,
        )
    if file is None:
        console.print("[red]Error:[/] FILE is required unless --interactive is used.")
        raise typer.Exit(code=1)
    orig_path = Path(file).expanduser().absolute()
    new_path = get_backup_path(orig_path=orig_path, sensitivity=sensitivity, destination=destination, shared=shared)
    if not _path_exists_for_register(orig_path) and not _path_exists_for_register(new_path):
        console.print(f"[red]Error:[/] Neither original file nor self-managed file exists:\n  Original: {orig_path}\n  Self-managed: {new_path}")
        raise typer.Exit(code=1)
    new_path.parent.mkdir(parents=True, exist_ok=True)
    match method:
        case "copy" | "c":
            try:
                result = copy_map(
                    config_file_default_path=orig_path,
                    config_file_self_managed_path=new_path,
                    on_conflict=ON_CONFLICT_MAPPER[on_conflict],
                )
            except Exception as e:
                msg = typer.style("Error: ", fg=typer.colors.RED) + str(e)
                typer.echo(msg)
                raise typer.Exit(code=1) from e
        case "symlink" | "s":
            try:
                result = symlink_map(
                    config_file_default_path=orig_path,
                    config_file_self_managed_path=new_path,
                    on_conflict=ON_CONFLICT_MAPPER[on_conflict],
                )
            except Exception as e:
                msg = typer.style("Error: ", fg=typer.colors.RED) + str(e)
                typer.echo(msg)
                raise typer.Exit(code=1) from e
        case _:
            raise ValueError(f"Unknown method: {method}")
    if result["action"] == "error":
        raise typer.Exit(code=1)
    entry_name = _resolve_entry_name(orig_path, name)
    if record:
        record_mapping(orig_path=orig_path, new_path=new_path, method=method, section=section, os_filter=os_filter, entry_name=entry_name)
        return
    preview = _build_mapper_preview(
        section=section,
        entry_name=entry_name,
        entry=_build_mapper_entry(
            original_path=orig_path,
            self_managed_path=new_path,
            method=METHOD_MAP[method],
            is_contents=False,
            os_filter=os_filter,
        ),
    )
    console.print(
        Panel(
            "\n".join(
                [
                    "✅ Dotfile mapping applied successfully.",
                    "🔄 Add the following YAML to mapper.yaml to persist this mapping:",
                    "",
                    preview,
                ]
            ),
            title="Mapping Preview",
            border_style="green",
            padding=(1, 2),
        )
    )


def edit_dotfile(
    editor: Annotated[
        Literal["nano", "hx", "code"],
        typer.Option("--editor", "-e", help="📝 Editor to open the dotfiles mapper.yaml file."),
    ] = "hx",
    source: Annotated[
        CONFIG_FILE_SOURCE_LOOSE,
        typer.Option("--source", "-s", help="📁 Which mapper file to edit: 'user' or 'library'."),
    ] = "user",
) -> None:
    source_key = CONFIG_FILE_SOURCE_MAP[source]
    if source_key == "user":
        file_path = USER_MAPPER_PATH
        file_path.parent.mkdir(parents=True, exist_ok=True)
        if not file_path.exists():
            write_dotfiles_mapper(path=file_path, mapper={}, header=DEFAULT_DOTFILE_MAPPER_HEADER)
    else:
        file_path = LIBRARY_MAPPER_PATH
        if not file_path.exists():
            msg = typer.style("Error: ", fg=typer.colors.RED) + f"Library mapper file not found: {file_path}"
            typer.echo(msg)
            raise typer.Exit(code=1)

    editor_bin = shutil.which(editor)
    if editor_bin is None:
        msg = typer.style("Error: ", fg=typer.colors.RED) + f"Editor '{editor}' is not available on PATH."
        typer.echo(msg)
        raise typer.Exit(code=1)

    result = subprocess.run([editor_bin, str(file_path)], check=False)
    if result.returncode != 0:
        msg = typer.style("Error: ", fg=typer.colors.RED) + f"Editor exited with status code {result.returncode}."
        typer.echo(msg)
        raise typer.Exit(code=result.returncode)


def arg_parser() -> None:
    typer.run(register_dotfile)


if __name__ == "__main__":
    arg_parser()
