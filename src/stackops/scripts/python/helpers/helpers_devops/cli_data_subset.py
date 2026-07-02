from copy import deepcopy
from pathlib import Path
from typing import Annotated, NoReturn

import typer

from stackops.profile.dotfiles_mapper import ALL_OS_VALUES
from stackops.profile.linking.options import CONFIG_FILE_SOURCE_LOOSE, CONFIG_FILE_SOURCE_MAP
from stackops.scripts.python.helpers.helpers_cloud.backup_config import (
    LIBRARY_BACKUP_PATH,
    USER_BACKUP_PATH,
    BackupConfig,
    BackupItem,
    load_backup_config_file,
)
from stackops.scripts.python.helpers.helpers_cloud.backup_selection import (
    BackupEntryKey,
    parse_backup_entry_selectors,
    resolve_backup_entry_keys,
)
from stackops.scripts.python.helpers.helpers_devops.cli_data_subset_io import load_existing_subset_output, write_subset_output
from stackops.scripts.python.helpers.helpers_devops.cli_interactive_picker import InteractivePickerOption, choose_interactive_options
from stackops.scripts.python.helpers.helpers_devops.cli_subset_support import (
    SUBSET_OUTPUT_CONFLICT_ACTIONS,
    SubsetOutputConflictAction,
    SubsetOutputConflictOption,
    resolve_subset_output_path,
)

DATA_SUBSET_HELP = "Create a backup configuration from selected data entries."


def subset(
    output_path: Annotated[Path, typer.Argument(help="Output data YAML path. Default mode creates a new file and refuses existing paths.")],
    which: Annotated[
        str | None,
        typer.Option(
            "--which",
            "-w",
            help="Comma-separated group or group.item selectors, or 'all'. A group selects all its entries; omit to choose interactively.",
        ),
    ] = None,
    source: Annotated[
        CONFIG_FILE_SOURCE_LOOSE,
        typer.Option("--source", "-s", case_sensitive=False, help="Source backup configuration file to read: user/u or library/l."),
    ] = "user",
    on_conflict: Annotated[
        SubsetOutputConflictOption,
        typer.Option(
            "--on-conflict", "-o", case_sensitive=False, help="How to handle an existing output path: throw-error/t, overwrite/o, or append/a."
        ),
    ] = "throw-error",
) -> None:
    """📦 <u> Create a backup configuration from selected data entries."""
    source_key = CONFIG_FILE_SOURCE_MAP[source]
    match source_key:
        case "library":
            source_path = LIBRARY_BACKUP_PATH
        case "user":
            source_path = USER_BACKUP_PATH
    subset_data_file(
        source_path=source_path,
        output_path=resolve_subset_output_path(output_path),
        on_conflict=SUBSET_OUTPUT_CONFLICT_ACTIONS[on_conflict],
        which=which,
    )


def subset_data_file(source_path: Path, output_path: Path, *, on_conflict: SubsetOutputConflictAction, which: str | None) -> None:
    source_config = _load_source_config(source_path)
    load_existing_subset_output(source_path=source_path, output_path=output_path, on_conflict=on_conflict)
    if which is None:
        selected_keys = _choose_subset_entry_keys(config=source_config, source_path=source_path)
    else:
        try:
            selectors = parse_backup_entry_selectors(which)
            selected_keys = resolve_backup_entry_keys(config=source_config, selectors=selectors)
        except ValueError as exc:
            _fail(str(exc))
    selected_config = _build_selected_config(source_config=source_config, selected_keys=selected_keys)
    existing_output_config = load_existing_subset_output(source_path=source_path, output_path=output_path, on_conflict=on_conflict)
    output_config = _merge_output_config(existing_output_config=existing_output_config, selected_config=selected_config)
    write_subset_output(source_path=source_path, output_path=output_path, output_config=output_config, on_conflict=on_conflict)
    selected_count = sum(len(group) for group in selected_config.values())
    action = "Appended" if on_conflict == "append" else "Wrote"
    suffix = f"; output now has {sum(len(group) for group in output_config.values())} entry(ies)" if on_conflict == "append" else ""
    typer.echo(
        typer.style("✅ Success: ", fg=typer.colors.GREEN)
        + f"{action} {selected_count} selected backup configuration entry(ies) to {output_path}{suffix}"
    )


def _load_source_config(source_path: Path) -> BackupConfig:
    try:
        source_config = load_backup_config_file(source_path, empty_as_config=False)
    except ValueError as exc:
        _fail(f"Invalid source backup configuration file {source_path}: {exc}")
    if source_config is None:
        _fail(f"Source backup configuration file does not exist, is not a file, or contains no entries: {source_path}")
    return source_config


def _choose_subset_entry_keys(*, config: BackupConfig, source_path: Path) -> list[BackupEntryKey]:
    picker_options = [
        InteractivePickerOption(
            value=BackupEntryKey(group_name=group_name, item_name=item_name),
            label=f"{group_name}.{item_name} -> {item['path_local']}",
            preview=_entry_preview(group_name=group_name, item_name=item_name, item=item, source_path=source_path),
            disambiguator=f"{group_name}.{item_name}",
        )
        for group_name, group_items in config.items()
        for item_name, item in group_items.items()
    ]
    return choose_interactive_options(
        picker_options,
        missing_tool_message="Interactive data subset selection requires `tv` on PATH.",
        missing_selection_message="Interactive selection did not map to a backup configuration entry",
    )


def _entry_preview(*, group_name: str, item_name: str, item: BackupItem, source_path: Path) -> str:
    os_values = ", ".join(value for value in ALL_OS_VALUES if value in item["os"])
    path_cloud = item["path_cloud"] if item["path_cloud"] is not None else "null"
    share_url = item["share_url"] if item["share_url"] is not None else "null"
    encryption = item["encryption"] if item["encryption"] is not None else "null"
    return "\n".join(
        (
            f"# {group_name}.{item_name}",
            "",
            f"- File: `{source_path}`",
            f"- Local path: `{item['path_local']}`",
            f"- Cloud path: `{path_cloud}`",
            f"- Share URL: `{share_url}`",
            f"- Encryption: `{encryption}`",
            f"- Zip: `{str(item['zip']).lower()}`",
            f"- Relative to home: `{str(item['rel2home']).lower()}`",
            f"- OS: `{os_values}`",
            "",
        )
    )


def _build_selected_config(*, source_config: BackupConfig, selected_keys: list[BackupEntryKey]) -> BackupConfig:
    if not selected_keys:
        _fail("No backup configuration entries selected.")
    selected_key_set = set(selected_keys)
    selected_config: BackupConfig = {}
    for group_name, group_items in source_config.items():
        selected_group = {
            item_name: deepcopy(item)
            for item_name, item in group_items.items()
            if BackupEntryKey(group_name=group_name, item_name=item_name) in selected_key_set
        }
        if selected_group:
            selected_config[group_name] = selected_group
    selected_count = sum(len(group) for group in selected_config.values())
    if selected_count != len(selected_key_set):
        _fail("Selection did not map to every selected backup configuration entry.")
    return selected_config


def _merge_output_config(*, existing_output_config: BackupConfig | None, selected_config: BackupConfig) -> BackupConfig:
    if existing_output_config is None:
        return selected_config
    collisions = [
        f"{group_name}.{item_name}"
        for group_name, group_items in selected_config.items()
        for item_name in group_items
        if item_name in existing_output_config.get(group_name, {})
    ]
    if collisions:
        _fail(f"Cannot append backup configuration entries that already exist: {', '.join(collisions)}")
    output_config = deepcopy(existing_output_config)
    for group_name, group_items in selected_config.items():
        if group_name not in output_config:
            output_config[group_name] = {}
        output_config[group_name].update(group_items)
    return output_config


def _fail(message: str) -> NoReturn:
    typer.echo(typer.style("Error: ", fg=typer.colors.RED) + message)
    raise typer.Exit(code=1)
