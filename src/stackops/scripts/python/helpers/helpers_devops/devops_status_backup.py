from pathlib import Path
from platform import system
from typing import TypedDict

from rich import box
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from stackops.profile.dotfiles_constants import ALL_OS_VALUES
from stackops.scripts.python.helpers.helpers_cloud.backup_config import USER_BACKUP_PATH, BackupConfig, load_backup_config_file, os_applies
from stackops.scripts.python.helpers.helpers_cloud.backup_remote import backup_path_needs_default_cloud
from stackops.utils.source_of_truth import read_stackops_config_string


class BackupStatus(TypedDict):
    cloud_config: str | None
    cloud_selection_required: bool
    source_path: Path
    backup_items_count: int
    backup_items: BackupConfig


def check_backup_config() -> BackupStatus:
    try:
        cloud_config = read_stackops_config_string("default_rclone_config").strip() or None
    except (FileNotFoundError, KeyError):
        cloud_config = None

    backup_items = load_backup_config_file(USER_BACKUP_PATH, empty_as_config=True)
    if backup_items is None:
        if USER_BACKUP_PATH.exists():
            raise ValueError(f"""Could not load user backup configuration: {USER_BACKUP_PATH}""")
        backup_items = {}

    current_system = system()
    return {
        "cloud_config": cloud_config,
        "cloud_selection_required": cloud_config is None and any(
            backup_path_needs_default_cloud(entry["path_cloud"])
            for entries in backup_items.values()
            for entry in entries.values()
            if os_applies(entry["os"], system_name=current_system)
        ),
        "source_path": USER_BACKUP_PATH,
        "backup_items_count": sum(len(entries) for entries in backup_items.values()),
        "backup_items": backup_items,
    }


def render_backup_status(status: BackupStatus) -> Panel:
    summary = Table(show_header=False, box=None, padding=(0, 1), expand=False)
    summary.add_column("Property", style="cyan", no_wrap=True)
    summary.add_column("Value", style="white")
    summary.add_row("🌥️  Default Cloud", Text(status["cloud_config"] or "No default remote"))
    summary.add_row("📦 Backup Items", str(status["backup_items_count"]))
    summary.add_row("📚 Source", Text(str(status["source_path"])))
    if status["cloud_selection_required"]:
        summary.add_row("Cloud selection", "Required for entries without an explicit remote")

    items = Table(title="Backup items", box=box.SIMPLE_HEAD, header_style="bold cyan", expand=True, show_lines=True)
    items.add_column("Entry", ratio=2, overflow="fold")
    items.add_column("Local path", ratio=3, overflow="fold")
    items.add_column("Cloud path", ratio=2, overflow="fold")
    items.add_column("OS", ratio=1, overflow="fold")
    items.add_column("Options", ratio=2, overflow="fold")
    for group_name, entries in status["backup_items"].items():
        for entry_name, entry in entries.items():
            cloud_path = "Automatic" if entry["path_cloud"] in (None, "^") else entry["path_cloud"]
            operating_systems = ", ".join(value for value in ALL_OS_VALUES if value in entry["os"])
            archive = "zip" if entry["zip"] else "raw"
            encryption = entry["encryption"] if entry["encryption"] is not None else "unencrypted"
            path_mode = "home-relative" if entry["rel2home"] else "absolute"
            items.add_row(
                Text(f"""{group_name}.{entry_name}""", style="bold cyan"),
                Text(entry["path_local"]),
                Text(cloud_path),
                Text(operating_systems),
                Text(f"""{archive} · {encryption} · {path_mode}"""),
            )

    details = items if status["backup_items_count"] else Text("No backup items configured.", style="dim")
    border_style = "green" if status["backup_items_count"] and not status["cloud_selection_required"] else "yellow"
    return Panel(Group(summary, Text(""), details), title="Backup Configuration", border_style=border_style, padding=(1, 1))
