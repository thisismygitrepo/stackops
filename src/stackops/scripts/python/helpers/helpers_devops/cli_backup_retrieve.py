"""BR: Backup and Retrieve"""

import shlex
from pathlib import Path
from platform import system
from typing import Literal

from rich.console import Console
from rich.panel import Panel

from stackops.utils.source_of_truth import read_stackops_config_string
from stackops.utils.meta import print_code
from stackops.utils.options_utils.options import choose_cloud_interactively
from stackops.scripts.python.helpers.helpers_cloud.cloud_path_resolver import ES
from stackops.scripts.python.helpers.helpers_cloud.backup_config import (
    BackupConfig,
    BackupGroup,
    BackupItem,
    describe_missing_backup_config,
    normalize_os_name,
    os_applies,
    read_backup_config,
)
from stackops.scripts.python.helpers.helpers_cloud.backup_registration import all_os_values
from stackops.profile.linking.options import CONFIG_SOURCE_LOOSE

DIRECTION = Literal["BACKUP", "RETRIEVE"]



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


def _is_http_url(value: str) -> bool:
    from urllib.parse import urlparse

    parsed_url = urlparse(value)
    return parsed_url.scheme in {"http", "https"} and parsed_url.netloc != ""


def _format_entry_names(entry_names: list[str]) -> str:
    return "\n".join(f"- {entry_name}" for entry_name in entry_names)


def _validate_use_link_items(items: BackupConfig) -> None:
    missing_share_url: list[str] = []
    invalid_share_url: list[str] = []
    for group_name, group_items in items.items():
        for item_name, item in group_items.items():
            display_name = f"{group_name}.{item_name}"
            share_url = item["share_url"]
            if share_url is None:
                missing_share_url.append(display_name)
            elif not _is_http_url(share_url):
                invalid_share_url.append(display_name)
    if not missing_share_url and not invalid_share_url:
        return

    message_parts = [
        "--use-link requires every selected sync-down entry to define a non-null http(s) share_url.",
    ]
    if missing_share_url:
        message_parts.append("Entries with share_url: null:")
        message_parts.append(_format_entry_names(missing_share_url))
    if invalid_share_url:
        message_parts.append("Entries with invalid share_url values:")
        message_parts.append(_format_entry_names(invalid_share_url))
    message_parts.append("Remove --use-link to use rclone, or add a valid share_url for each selected entry.")
    raise ValueError("\n".join(message_parts))


def _retrieve_from_share_url(
    *,
    display_name: str,
    item: BackupItem,
    local_path: Path,
    pwd: str | None,
    overwrite: bool,
) -> Path:
    from stackops.scripts.python.helpers.helpers_cloud.cloud_copy import (
        ShareUrlDownloadError,
        download_from_share_url,
    )
    from stackops.utils.io import GpgCommandError

    share_url = item["share_url"]
    if share_url is None:
        raise ValueError(f"Backup entry '{display_name}' has share_url: null.")
    try:
        return download_from_share_url(
            share_url=share_url,
            target_path=local_path,
            zip_requested=item["zip"],
            encrypt_requested=item["encrypt"],
            encryption_mode=item["encryption"],
            pwd=pwd if item["encryption"] == "symmetric" else None,
            overwrite=overwrite,
        )
    except ShareUrlDownloadError as error:
        raise ValueError(f"Could not retrieve '{display_name}' with --use-link: {error}") from error
    except GpgCommandError as error:
        raise ValueError(f"Could not decrypt '{display_name}' after downloading its share_url.\n{error}") from error



def _parse_requested_backup_entries(which: str) -> list[str]:
    choices = [token.strip() for token in which.split(",")]
    if not choices or any(not token for token in choices):
        raise ValueError("Invalid --which value: expected a comma-separated list of non-empty group or group.item names, or 'all'.")
    if "all" in choices and len(choices) != 1:
        raise ValueError("Invalid --which value: 'all' cannot be combined with other entries.")
    return choices


def main_backup_retrieve(
    direction: DIRECTION,
    which: str | None,
    cloud: str | None,
    source: CONFIG_SOURCE_LOOSE,
    use_link: bool = False,
    pwd: str | None = None,
) -> None:
    console = Console()
    if pwd == "":
        raise ValueError("--password must be non-empty.")
    if use_link and direction != "RETRIEVE":
        raise ValueError("--use-link can only be used with sync down/d. Backups still use rclone.")
    use_link_retrieve = use_link and direction == "RETRIEVE"
    bu_file = read_backup_config(source=source)
    if bu_file is None:
        raise ValueError(describe_missing_backup_config(source=source))
    cloud_override = cloud.strip() if cloud and cloud.strip() else None
    fallback_cloud: str | None = None
    if use_link_retrieve:
        cloud_message = "🔗 LINK RETRIEVE MODE\n⬇️  Using share_url downloads instead of rclone."
        if cloud_override is not None:
            cloud_message += "\n☁️  --cloud was provided but is ignored in link mode."
        console.print(Panel(cloud_message, title="[bold blue]Link Retrieve[/bold blue]", border_style="blue"))
    elif cloud_override is None:
        try:
            default_cloud = read_stackops_config_string("default_rclone_config").strip()
            if default_cloud:
                fallback_cloud = default_cloud
                console.print(Panel(f"⚠️  DEFAULT CLOUD CONFIGURATION\n🌥️  Using default cloud: {fallback_cloud}", title="[bold blue]Cloud Configuration[/bold blue]", border_style="blue"))
            else:
                console.print(Panel("🔍 DEFAULT CLOUD NOT FOUND\n📝 Entries with an explicit cloud in path_cloud can still run. Entries without one will prompt for a cloud.", title="[bold yellow]Cloud Configuration[/bold yellow]", border_style="yellow"))
        except (FileNotFoundError, KeyError, ValueError):
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
    if use_link_retrieve:
        _validate_use_link_items(items)
    program = ""
    link_download_count = 0
    needs_fallback_cloud = (
        not use_link_retrieve
        and cloud_override is None
        and fallback_cloud is None
        and any(_path_cloud_needs_default_cloud(item["path_cloud"]) for group_items in items.values() for item in group_items.values())
    )
    if needs_fallback_cloud:
        console.print(Panel("🔍 CLOUD NOT FOUND\n🔄 Please select a cloud configuration from the options below", title="[bold red]Error: Cloud Not Found[/bold red]", border_style="red"))
        cloud_choice = choose_cloud_interactively()
        if cloud_choice is None:
            raise ValueError("Cloud selection cancelled.")
        fallback_cloud = cloud_choice.strip()
        if not fallback_cloud:
            raise ValueError("Cloud selection cancelled.")
    cloud_mode = "share_url links" if use_link_retrieve else cloud_override or fallback_cloud or "path_cloud-specific"
    operation_line = f"🔗 RUNNING {direction} VIA SHARE LINKS" if use_link_retrieve else f"🚀 GENERATING {direction} SCRIPT"
    operation_title = "[bold blue]Link Retrieve[/bold blue]" if use_link_retrieve else "[bold blue]Script Generation[/bold blue]"
    console.print(Panel(f"{operation_line}\n🌥️  Cloud: {cloud_mode}\n🗂️  Items: {sum(len(item) for item in items.values())}", title=operation_title, border_style="blue"))
    for group_name, group_items in items.items():
        for item_name, item in group_items.items():
            display_name = f"{group_name}.{item_name}"
            flags = ""
            flags += "z" if item["zip"] else ""
            flags += "e" if item["encrypt"] else ""
            flags += "r" if item["rel2home"] else ""
            flags += "o" if not all_os_values(item["os"]) else ""
            encryption_mode = item["encryption"]
            if item["encrypt"] and encryption_mode is None:
                raise ValueError(f"Backup entry '{display_name}' must define 'encryption' when 'encrypt' is true.")
            encryption_arg = f" --encryption {encryption_mode}" if item["encrypt"] else ""
            password_arg = f" --password {shlex.quote(pwd)}" if encryption_mode == "symmetric" and pwd is not None else ""
            local_path = Path(item["path_local"]).as_posix()
            path_cloud = item["path_cloud"]
            if use_link_retrieve:
                console.print(Panel(
                    f"📦 PROCESSING: {display_name}\n"
                    f"📂 Local path: {local_path}\n"
                    "🔗 Source: share_url\n"
                    f"🔐 Encryption: {item['encryption'] if item['encrypt'] else 'None'}\n"
                    f"🏳️  Flags: {flags or 'None'}",
                    title=f"[bold blue]Processing Link Item: {display_name}[/bold blue]",
                    border_style="blue",
                ))
                final_path = _retrieve_from_share_url(
                    display_name=display_name,
                    item=item,
                    local_path=Path(local_path),
                    pwd=pwd,
                    overwrite=not all_os_values(item["os"]),
                )
                link_download_count += 1
                console.print(Panel(f"✅ Downloaded and restored: {final_path}", title="[bold green]Link Retrieve[/bold green]", border_style="green"))
                if group_name == "dotfiles" and system_raw == "Linux":
                    program += """\nchmod 700 ~/.ssh/*\n"""
                    console.print(Panel("🔒 SPECIAL HANDLING: SSH PERMISSIONS\n🛠️  Setting secure permissions for SSH files\n📝 Command: chmod 700 ~/.ssh/*", title="[bold blue]Special Handling: SSH Permissions[/bold blue]", border_style="blue"))
                continue
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
                program += f"""\ncloud copy "{local_path}" "{remote_spec}"{flag_arg}{encryption_arg}{password_arg}\n"""
            elif direction == "RETRIEVE":
                program += f"""\ncloud copy "{remote_spec}" "{local_path}"{flag_arg}{encryption_arg}{password_arg}\n"""
            else:
                console.print(Panel('❌ ERROR: INVALID DIRECTION\n⚠️  Direction must be either "BACKUP" or "RETRIEVE"', title="[bold red]Error: Invalid Direction[/bold red]", border_style="red"))
                raise RuntimeError(f"Unknown direction: {direction}")
            if group_name == "dotfiles" and system_raw == "Linux":
                program += """\nchmod 700 ~/.ssh/*\n"""
                console.print(Panel("🔒 SPECIAL HANDLING: SSH PERMISSIONS\n🛠️  Setting secure permissions for SSH files\n📝 Command: chmod 700 ~/.ssh/*", title="[bold blue]Special Handling: SSH Permissions[/bold blue]", border_style="blue"))
    if program.strip():
        script_desc = f"{direction} post-processing script" if use_link_retrieve else f"{direction} script"
        print_code(code=program, lexer="shell", desc=script_desc)
        console.print(Panel(f"✅ {direction} SCRIPT GENERATION COMPLETE\n🚀 Ready to execute the operations", title="[bold green]Script Generation Complete[/bold green]", border_style="green"))
        # import subprocess
        # subprocess.run(program, shell=True, check=True)
        from stackops.utils.code import run_shell_script
        run_shell_script(program, display_script=True, clean_env=False)
    if link_download_count:
        console.print(Panel(f"✅ LINK RETRIEVE COMPLETE\n🔢 Downloaded entries: {link_download_count}", title="[bold green]Link Retrieve Complete[/bold green]", border_style="green"))
    elif not program.strip():
        console.print(Panel(f"✅ {direction} COMPLETE\nNo shell commands were generated.", title="[bold green]Complete[/bold green]", border_style="green"))


if __name__ == "__main__":
    pass
