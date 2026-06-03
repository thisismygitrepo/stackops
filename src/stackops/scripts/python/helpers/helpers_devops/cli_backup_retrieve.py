"""BR: Backup and Retrieve"""

import re
from pathlib import Path
from platform import system
from typing import Literal, cast

from rich.console import Console
from rich.panel import Panel

from stackops.profile.dotfiles_mapper import ALL_OS_VALUES, OsName
from stackops.utils.io import read_ini
from stackops.utils.source_of_truth import DEFAULTS_PATH
from stackops.utils.code import print_code
from stackops.utils.options import choose_cloud_interactively
from stackops.scripts.python.helpers.helpers_cloud.helpers2 import ES
from stackops.scripts.python.helpers.helpers_devops.backup_config import (
    BackupConfig,
    BackupGroup,
    VALID_OS,
    USER_BACKUP_PATH,
    describe_missing_backup_config,
    normalize_os_name,
    os_applies,
    read_backup_config,
    read_user_backup_config_for_update,
    write_backup_config,
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
    return cast(OsName, token)


def _split_remote_spec(value: str) -> tuple[str, str] | None:
    if ":" not in value or (len(value) > 1 and value[1] == ":"):
        return None
    cloud_name, remote_value = value.split(":", 1)
    if not cloud_name or not remote_value:
        return None
    return cloud_name, remote_value


def _path_cloud_needs_default_cloud(path_cloud: str | None) -> bool:
    if path_cloud in (None, ES):
        return True
    return _split_remote_spec(path_cloud) is None


def register_backup_entry(
    path_local: str,
    group: str,
    entry_name: str | None = None,
    path_cloud: str | None = None,
    share_url: str | None = None,
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
    share_url_value = share_url.strip() if share_url and share_url.strip() else None
    USER_BACKUP_PATH.parent.mkdir(parents=True, exist_ok=True)
    if USER_BACKUP_PATH.exists():
        config = read_user_backup_config_for_update()
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
        "share_url": share_url_value,
        "zip": zip_,
        "encrypt": encrypt,
        "rel2home": rel2home,
        "os": set(os_tokens),
    }
    write_backup_config(USER_BACKUP_PATH, config)
    return USER_BACKUP_PATH, entry_name, replaced


def _parse_requested_backup_entries(which: str) -> list[str]:
    choices = [token.strip() for token in which.split(",")]
    if not choices or any(not token for token in choices):
        raise ValueError("Invalid --which value: expected a comma-separated list of non-empty group or group.item names, or 'all'.")
    if "all" in choices and len(choices) != 1:
        raise ValueError("Invalid --which value: 'all' cannot be combined with other entries.")
    return choices


def main_backup_retrieve(direction: DIRECTION, which: str | None, cloud: str | None, repo: REPO_LOOSE) -> None:
    console = Console()
    bu_file = read_backup_config(repo=repo)
    if bu_file is None:
        raise ValueError(describe_missing_backup_config(repo=repo))
    cloud_override = cloud.strip() if cloud and cloud.strip() else None
    fallback_cloud: str | None = None
    if cloud_override is None:
        try:
            default_cloud = read_ini(DEFAULTS_PATH)["general"]["rclone_config_name"].strip()
            if default_cloud:
                fallback_cloud = default_cloud
                console.print(Panel(f"⚠️  DEFAULT CLOUD CONFIGURATION\n🌥️  Using default cloud: {fallback_cloud}", title="[bold blue]Cloud Configuration[/bold blue]", border_style="blue"))
            else:
                console.print(Panel("🔍 DEFAULT CLOUD NOT FOUND\n📝 Entries with an explicit cloud in path_cloud can still run. Entries without one will prompt for a cloud.", title="[bold yellow]Cloud Configuration[/bold yellow]", border_style="yellow"))
        except (FileNotFoundError, KeyError, IndexError):
            console.print(Panel("🔍 DEFAULT CLOUD NOT FOUND\n📝 Entries with an explicit cloud in path_cloud can still run. Entries without one will prompt for a cloud.", title="[bold yellow]Cloud Configuration[/bold yellow]", border_style="yellow"))
    else:
        console.print(Panel(f"🌥️  Using provided cloud: {cloud_override}", title="[bold blue]Cloud Configuration[/bold blue]", border_style="blue"))
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
            raise ValueError("No backup entries selected.")
    else:
        choices = _parse_requested_backup_entries(which)
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
        if not items:
            raise ValueError("No backup entries selected.")
        console.print(Panel(f"📋 PROCESSING SELECTED ENTRIES\n🔢 Total entries to process: {sum(len(item) for item in items.values())}", title="[bold blue]Process Selected Entries[/bold blue]", border_style="blue"))
    program = ""
    needs_fallback_cloud = cloud_override is None and fallback_cloud is None and any(_path_cloud_needs_default_cloud(item["path_cloud"]) for group_items in items.values() for item in group_items.values())
    if needs_fallback_cloud:
        console.print(Panel("🔍 CLOUD NOT FOUND\n🔄 Please select a cloud configuration from the options below", title="[bold red]Error: Cloud Not Found[/bold red]", border_style="red"))
        cloud_choice = choose_cloud_interactively()
        if cloud_choice is None:
            raise ValueError("Cloud selection cancelled.")
        fallback_cloud = cloud_choice.strip()
        if not fallback_cloud:
            raise ValueError("Cloud selection cancelled.")
    cloud_mode = cloud_override or fallback_cloud or "path_cloud-specific"
    console.print(Panel(f"🚀 GENERATING {direction} SCRIPT\n🌥️  Cloud: {cloud_mode}\n🗂️  Items: {sum(len(item) for item in items.values())}", title="[bold blue]Script Generation[/bold blue]", border_style="blue"))
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
            remote_spec_parts = _split_remote_spec(path_cloud) if path_cloud not in (None, ES) else None
            if remote_spec_parts is not None and cloud_override is None:
                item_cloud, remote_path = remote_spec_parts
                remote_display = f"{item_cloud}:{remote_path}"
                remote_spec = remote_display
            elif path_cloud in (None, ES):
                item_cloud = cloud_override or fallback_cloud
                if item_cloud is None:
                    raise ValueError(f"Backup entry '{display_name}' does not define a cloud in 'path_cloud', and no --cloud or default cloud is available.")
                remote_path = ES
                remote_display = f"{ES} (deduced)"
                remote_spec = f"{item_cloud}:{remote_path}"
            else:
                assert path_cloud is not None
                item_cloud = cloud_override or fallback_cloud
                if item_cloud is None:
                    raise ValueError(f"Backup entry '{display_name}' does not define a cloud in 'path_cloud', and no --cloud or default cloud is available.")
                remote_path = Path(remote_spec_parts[1] if remote_spec_parts is not None else path_cloud).as_posix()
                remote_display = remote_path
                remote_spec = f"{item_cloud}:{remote_path}"
            console.print(Panel(
                f"📦 PROCESSING: {display_name}\n"
                f"📂 Local path: {local_path}\n"
                f"☁️  Cloud: {item_cloud}\n"
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
