from typing import TypedDict

from rich import box
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from stackops.profile.dotfiles_constants import ALL_OS_VALUES
from stackops.scripts.python.helpers.helpers_cloud.backup_config import LIBRARY_BACKUP_PATH, BackupConfig, load_backup_config_file
from stackops.utils.source_of_truth import read_stackops_config_string


class BackupStatus(TypedDict):
    cloud_config: str
    backup_items_count: int
    backup_items: BackupConfig


def check_backup_config() -> BackupStatus:
    try:
        cloud_config = read_stackops_config_string("default_rclone_config")
    except (FileNotFoundError, KeyError):
        cloud_config = "Not configured"

    backup_items = load_backup_config_file(LIBRARY_BACKUP_PATH, empty_as_config=True)
    if backup_items is None:
        raise ValueError(f"""Could not load library backup configuration: {LIBRARY_BACKUP_PATH}""")

    return {
        "cloud_config": cloud_config,
        "backup_items_count": sum(len(entries) for entries in backup_items.values()),
        "backup_items": backup_items,
    }


def render_backup_status(status: BackupStatus) -> Panel:
    summary = Table(show_header=False, box=None, padding=(0, 1), expand=False)
    summary.add_column("Property", style="cyan", no_wrap=True)
    summary.add_column("Value", style="white")
    summary.add_row("🌥️  Cloud Config", Text(status["cloud_config"]))
    summary.add_row("📦 Backup Items", str(status["backup_items_count"]))
    summary.add_row("📚 Source", "Library")

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
    border_style = "green" if status["cloud_config"] != "Not configured" else "yellow"
    return Panel(Group(summary, Text(""), details), title="Backup Configuration", border_style=border_style, padding=(1, 1))
