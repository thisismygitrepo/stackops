from pathlib import Path
import platform
from typing import Literal

from rich import box
from rich.table import Table
from rich.text import Text

from stackops.scripts.python.helpers.helpers_cloud.cloud_path_resolver import ES
from stackops.utils.cloud.defaults import CloudConfig
from stackops.utils.cloud.rclone import ShareLinkOptions


def cloud_copy_summary(
    *,
    operation: Literal["download", "upload"],
    cloud: str,
    original_source: str,
    original_target: str,
    source: str,
    target: str,
    config: CloudConfig,
    transfers: int,
    share_options: ShareLinkOptions | None,
) -> Table:
    table = Table(
        title=f"""Cloud copy · {operation.title()}""",
        title_justify="left",
        show_header=False,
        box=box.ROUNDED,
        border_style="blue",
        padding=(0, 1),
    )
    table.add_column("Setting", style="bold", no_wrap=True)
    table.add_column("Resolution", overflow="fold")
    for label, original, resolved in (
        ("Source", original_source, source),
        ("Target", original_target, target),
    ):
        path_text = Text(original)
        if original != resolved:
            path_text.stylize("dim")
            path_text.append(f"""\n→ {resolved}""")
        table.add_row(label, path_text)

    remote_input = original_source if operation == "download" else original_target
    remote_text = Text(cloud)
    if remote_input.startswith(":"):
        remote_text.append(" (default remote)", style="dim")
    table.add_row("Remote", remote_text)

    if remote_input.partition(":")[2] == ES:
        local_path = Path(target if operation == "download" else source)
        local_role = "target" if operation == "download" else "source"
        table.add_row("^ expansion", f"""Derived from the local {local_role}""")
        table.add_row("Remote root", Text(config["root"]))
        table.add_row("OS folder", platform.system().lower() if config["os_specific"] else "generic_os")
        if config["rel2home"] and local_path.is_relative_to(Path.home()):
            path_base = f"""Relative to {Path.home()}"""
        elif config["rel2home"]:
            path_base = "Absolute local path (outside home)"
        else:
            path_base = "Absolute local path"
        table.add_row("Path base", Text(path_base))

    zip_action = "Extract after download" if operation == "download" else "Compress before upload"
    table.add_row("ZIP", zip_action if config["zip"] else "Off")
    encryption_mode = config["encryption"]
    encryption_action = "decrypt after download" if operation == "download" else "encrypt before upload"
    table.add_row("Encryption", "Off" if encryption_mode is None else f"""{encryption_mode.title()} — {encryption_action}""")
    table.add_row("Existing target", "Overwrite" if config["overwrite"] else "Reject conflicting files")
    table.add_row("Transfers", str(transfers))
    if operation == "upload" and share_options is not None:
        scope = share_options["scope"]
        link_type = share_options["link_type"]
        share_details = ", ".join(value for value in (scope, link_type) if value is not None)
        table.add_row("Share link", share_details)
    return table
