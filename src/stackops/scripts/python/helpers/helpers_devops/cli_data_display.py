import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from stackops.profile.dotfiles_mapper import ALL_OS_VALUES
from stackops.scripts.python.helpers.helpers_cloud.backup_config import (
    USER_BACKUP_PATH,
    describe_missing_backup_config,
    load_backup_config_file,
)
from stackops.scripts.python.helpers.helpers_cloud.backup_registration import BackupRegistrationResult


def show_registration_summary(registration: BackupRegistrationResult) -> None:
    entry = registration["entry"]
    os_values = ", ".join(value for value in ALL_OS_VALUES if value in entry["os"])
    path_cloud = entry["path_cloud"] if entry["path_cloud"] is not None else "null"
    share_url = entry["share_url"] if entry["share_url"] is not None else "null"
    encryption = entry["encryption"] if entry["encryption"] is not None else "null"

    details = Table.grid(padding=(0, 2), expand=True)
    details.add_column(style="bold cyan", no_wrap=True)
    details.add_column(overflow="fold")
    details.add_row("Entry", Text(f"{registration['group_name']}.{registration['entry_name']}"))
    details.add_row("Local path", Text(entry["path_local"]))
    details.add_row("Cloud path", Text(path_cloud))
    details.add_row("Share URL", Text(share_url))
    details.add_row("Zip", Text(str(entry["zip"]).lower()))
    details.add_row("Encryption", Text(encryption))
    details.add_row("Home-relative", Text(str(entry["rel2home"]).lower()))
    details.add_row("OS", Text(os_values))
    details.add_row("Data file", Text(registration["backup_path"].as_posix()))

    action = "Updated" if registration["replaced"] else "Added"
    icon = "♻️" if registration["replaced"] else "✅"
    border_style = "cyan" if registration["replaced"] else "green"
    Console().print(
        Panel(
            details,
            title=f"{icon} Backup Entry {action}",
            border_style=border_style,
            padding=(1, 2),
        )
    )


def display_data() -> None:
    try:
        config = load_backup_config_file(USER_BACKUP_PATH, empty_as_config=True)
    except ValueError as exc:
        typer.echo(typer.style("Error: ", fg=typer.colors.RED) + str(exc), err=True)
        raise typer.Exit(code=1) from exc
    if config is None:
        if USER_BACKUP_PATH.exists():
            typer.echo(typer.style("Error: ", fg=typer.colors.RED) + describe_missing_backup_config(source="user"), err=True)
            raise typer.Exit(code=1)
        config = {}

    console = Console()
    entry_count = sum(len(group_entries) for group_entries in config.values())
    if entry_count == 0:
        console.print(
            Panel(
                Text(f"No registered backup entries found in {USER_BACKUP_PATH}"),
                title="No Backup Entries",
                border_style="yellow",
                padding=(1, 2),
            )
        )
        return

    table = Table(
        title=f"Registered Backup Entries ({entry_count})",
        caption=Text(f"Data file: {USER_BACKUP_PATH}", style="dim"),
        caption_justify="left",
        box=box.SIMPLE_HEAVY,
        expand=True,
        header_style="bold cyan",
    )
    table.add_column("Entry", ratio=2, overflow="fold")
    table.add_column("Local path", ratio=3, overflow="fold")
    table.add_column("Cloud path", ratio=2, overflow="fold")
    table.add_column("OS", ratio=2, overflow="fold")
    table.add_column("Options", ratio=2, overflow="fold")
    table.add_column("Share URL", ratio=2, overflow="fold")

    for group_name, group_entries in config.items():
        for entry_name, entry in group_entries.items():
            path_cloud = entry["path_cloud"] if entry["path_cloud"] is not None else "null"
            share_url = entry["share_url"] if entry["share_url"] is not None else "null"
            encryption = entry["encryption"] if entry["encryption"] is not None else "null"
            os_values = ", ".join(value for value in ALL_OS_VALUES if value in entry["os"])
            archive_mode = "zip" if entry["zip"] else "raw"
            path_mode = "home-relative" if entry["rel2home"] else "absolute"

            table.add_row(
                Text(f"{group_name}.{entry_name}", style="bold cyan"),
                Text(entry["path_local"]),
                Text(path_cloud),
                Text(os_values),
                Text(f"{archive_mode} · {encryption} · {path_mode}"),
                Text(share_url),
            )

    console.print(table)
