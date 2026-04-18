"""BR: Backup and Retrieve"""

import re
from platform import system
from typing import Literal
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from stackops.profile.dotfiles_mapper import ALL_OS_VALUES, OsName
from stackops.utils.io import read_ini
from stackops.utils.source_of_truth import DEFAULTS_PATH
from stackops.utils.code import print_code
from stackops.utils.options import choose_cloud_interactively
from stackops.scripts.python.helpers.helpers_cloud.helpers2 import ES
from stackops.scripts.python.helpers.helpers_devops.backup_config import (
    BackupConfig, BackupGroup, VALID_OS, USER_BACKUP_PATH,
    describe_missing_backup_config,
    normalize_os_name, os_applies, read_backup_config, write_backup_config,
)
from stackops.profile.create_links_export import REPO_LOOSE

DIRECTION = Literal["BACKUP", "RETRIEVE"]


def _sanitize_entry_name(value: str) -> str:
    token = value.strip().replace(".", "_").replace("-", "_")
    token = re.sub(r"\s+", "_", token)
    token = re.sub(r"[^A-Za-z0-9_]", "_", token)
    return token or "backup_item"


def _is_all_os_values(os_values: set[OsName]) -> bool:
    return len(os_values) == len(ALL_OS_VALUES) and all(value in os_values for value in ALL_OS_VALUES)


def _require_os_name(value: str, *, os_filter: str) -> OsName:
    token = normalize_os_name(value)
    if token not in VALID_OS:
        raise ValueError(f"Invalid os value: {os_filter!r}. Expected one of: {sorted(VALID_OS)}")
    return token


def register_backup_entry(
    path_local: str,
    group: str,
    entry_name: str | None = None,
    path_cloud: str | None = None,
    zip_: bool = True,
    encrypt: bool = True,
    rel2home: bool | None = None,
    os: str = "",
) -> tuple[Path, str, bool]:
    local_path = Path(path_local).expanduser().absolute()
    if not local_path.exists():
        raise ValueError(f"Local path does not exist: {local_path}")
    os_parts = [part.strip() for part in os.split(",")]
    os_tokens_unsorted: set[OsName] = set()
    for part in os_parts:
        if not part:
            continue
        os_tokens_unsorted.add(_require_os_name(part, os_filter=os))
    os_tokens = sorted(os_tokens_unsorted, key=ALL_OS_VALUES.index)
    if not os_tokens:
        raise ValueError(f"Invalid os value: {os!r}. Expected one of: {sorted(VALID_OS)}")
    home = Path.home()
    in_home = local_path.is_relative_to(home)
    if rel2home is None:
        rel2home = in_home
    if rel2home and not in_home:
        raise ValueError("rel2home is true, but the local path is not under the home directory.")
    group_name = _sanitize_entry_name(group) if group and group.strip() else "default"
    if entry_name is None or not entry_name.strip():
        base_name = _sanitize_entry_name(local_path.stem)
        entry_name = base_name if _is_all_os_values(set(os_tokens)) else f"{base_name}_{'_'.join(os_tokens)}"
    else:
        entry_name = _sanitize_entry_name(entry_name)
    local_display = f"~/{local_path.relative_to(home)}" if rel2home and in_home else local_path.as_posix()
    cloud_value = path_cloud.strip() if path_cloud and path_cloud.strip() else ES
    USER_BACKUP_PATH.parent.mkdir(parents=True, exist_ok=True)
    if USER_BACKUP_PATH.exists():
        config = read_backup_config(repo="user")
        if config is None:
            raise ValueError(describe_missing_backup_config(repo="user"))
    else:
        config = {}
    if group_name in config:
        group_entries = config[group_name]
    else:
        group_entries = {}
        config[group_name] = group_entries
    replaced = entry_name in group_entries
    group_entries[entry_name] = {
        "path_local": local_display,
        "path_cloud": cloud_value,
        "zip": zip_,
        "encrypt": encrypt,
        "rel2home": rel2home,
        "os": set(os_tokens),
    }
    write_backup_config(USER_BACKUP_PATH, config)
    return USER_BACKUP_PATH, entry_name, replaced


def main_backup_retrieve(direction: DIRECTION, which: str | None, cloud: str | None, repo: REPO_LOOSE) -> None:
    console = Console()
    bu_file = read_backup_config(repo=repo)
    if bu_file is None:
        raise ValueError(describe_missing_backup_config(repo=repo))
    if cloud is None or not cloud.strip():
        try:
            cloud = read_ini(DEFAULTS_PATH)["general"]["rclone_config_name"].strip()
            console.print(Panel(f"⚠️  DEFAULT CLOUD CONFIGURATION\n🌥️  Using default cloud: {cloud}", title="[bold blue]Cloud Configuration[/bold blue]", border_style="blue"))
        except (FileNotFoundError, KeyError, IndexError):
            console.print(Panel("🔍 DEFAULT CLOUD NOT FOUND\n🔄 Please select a cloud configuration from the options below", title="[bold red]Error: Cloud Not Found[/bold red]", border_style="red"))
            cloud_choice = choose_cloud_interactively()
            if cloud_choice is None:
                console.print(Panel("❓ Cloud selection cancelled.", title="[bold yellow]Cancelled[/bold yellow]", border_style="yellow"))
                return
            cloud = cloud_choice.strip()
    else:
        cloud = cloud.strip()
        console.print(Panel(f"🌥️  Using provided cloud: {cloud}", title="[bold blue]Cloud Configuration[/bold blue]", border_style="blue"))
    assert cloud is not None
    system_raw = system()
    normalized_system = normalize_os_name(system_raw)
    filtered: BackupConfig = {}
    for group_name, group_items in bu_file.items():
        matched: BackupGroup = {}
        for key, val in group_items.items():
            if os_applies(val["os"], system_name=normalized_system):
                matched[key] = val
        if matched:
            filtered[group_name] = matched
    bu_file = filtered
    applicable_entry_count = sum(len(item) for item in bu_file.values())
    if applicable_entry_count == 0:
        raise ValueError(f"No backup configuration entries apply to the current OS: {normalized_system}")
    console.print(Panel(
        f"🖥️  {system_raw} ENVIRONMENT DETECTED\n"
        "🔍 Filtering entries by os field\n"
        f"✅ Found {applicable_entry_count} applicable backup configuration entries",
        title="[bold blue]Environment[/bold blue]",
        border_style="blue",
    ))

    if which is None:
        from stackops.utils.options_utils.tv_options import choose_from_dict_with_preview
        choices = choose_from_dict_with_preview(
            options_to_preview_mapping=bu_file, extension="yaml", multi=True, preview_size_percent=75.0,
        )
        if len(choices) == 0:
            console.print(Panel("❌ NO ITEMS SELECTED\n⚠️  Exiting without processing any items", title="[bold red]No Items Selected[/bold red]", border_style="red"))
            return
    else:
        choices = [token.strip() for token in which.split(",")] if which else []
        console.print(Panel(f"🔖 PRE-SELECTED ITEMS\n📝 Using: {', '.join(choices)}", title="[bold blue]Pre-selected Items[/bold blue]", border_style="blue"))

    items: BackupConfig
    if "all" in choices:
        items = bu_file
        console.print(Panel(f"📋 PROCESSING ALL ENTRIES\n🔢 Total entries to process: {sum(len(item) for item in bu_file.values())}", title="[bold blue]Process All Entries[/bold blue]", border_style="blue"))
    else:
        items = {}
        unknown: list[str] = []
        for choice in choices:
            if not choice:
                continue
            if choice in bu_file:
                items[choice] = bu_file[choice]
                continue
            if "." in choice:
                group_name, item_name = choice.split(".", 1)
                if group_name in bu_file and item_name in bu_file[group_name]:
                    items.setdefault(group_name, {})[item_name] = bu_file[group_name][item_name]
                    continue
            unknown.append(choice)
        if unknown:
            raise ValueError(f"Unknown backup entries: {', '.join(unknown)}")
        console.print(Panel(f"📋 PROCESSING SELECTED ENTRIES\n🔢 Total entries to process: {sum(len(item) for item in items.values())}", title="[bold blue]Process Selected Entries[/bold blue]", border_style="blue"))
    program = ""
    console.print(Panel(f"🚀 GENERATING {direction} SCRIPT\n🌥️  Cloud: {cloud}\n🗂️  Items: {sum(len(item) for item in items.values())}", title="[bold blue]Script Generation[/bold blue]", border_style="blue"))
    for group_name, group_items in items.items():
        for item_name, item in group_items.items():
            display_name = f"{group_name}.{item_name}"
            flags = ""
            flags += "z" if item["zip"] else ""
            flags += "e" if item["encrypt"] else ""
            flags += "r" if item["rel2home"] else ""
            flags += "o" if not _is_all_os_values(item["os"]) else ""
            local_path = Path(item["path_local"]).as_posix()
            path_cloud = item["path_cloud"]
            if path_cloud in (None, ES):
                remote_path = ES
                remote_display = f"{ES} (deduced)"
            else:
                assert path_cloud is not None
                remote_path = Path(path_cloud).as_posix()
                remote_display = remote_path
            remote_spec = f"{cloud}:{remote_path}"
            console.print(Panel(
                f"📦 PROCESSING: {display_name}\n"
                f"📂 Local path: {local_path}\n"
                f"☁️  Remote path: {remote_display}\n"
                f"🏳️  Flags: {flags or 'None'}",
                title=f"[bold blue]Processing Item: {display_name}[/bold blue]",
                border_style="blue",
            ))
            flag_arg = f" -{flags}" if flags else ""
            if direction == "BACKUP":
                program += f"""\ncloud copy "{local_path}" "{remote_spec}"{flag_arg}\n"""
            elif direction == "RETRIEVE":
                program += f"""\ncloud copy "{remote_spec}" "{local_path}"{flag_arg}\n"""
            else:
                console.print(Panel('❌ ERROR: INVALID DIRECTION\n⚠️  Direction must be either "BACKUP" or "RETRIEVE"', title="[bold red]Error: Invalid Direction[/bold red]", border_style="red"))
                raise RuntimeError(f"Unknown direction: {direction}")
            if group_name == "dotfiles" and system_raw == "Linux":
                program += """\nchmod 700 ~/.ssh/*\n"""
                console.print(Panel("🔒 SPECIAL HANDLING: SSH PERMISSIONS\n🛠️  Setting secure permissions for SSH files\n📝 Command: chmod 700 ~/.ssh/*", title="[bold blue]Special Handling: SSH Permissions[/bold blue]", border_style="blue"))
    print_code(code=program, lexer="shell", desc=f"{direction} script")
    console.print(Panel(f"✅ {direction} SCRIPT GENERATION COMPLETE\n🚀 Ready to execute the operations", title="[bold green]Script Generation Complete[/bold green]", border_style="green"))
    # import subprocess
    # subprocess.run(program, shell=True, check=True)
    from stackops.utils.code import run_shell_script
    run_shell_script(program, display_script=True, clean_env=False)


if __name__ == "__main__":
    pass
