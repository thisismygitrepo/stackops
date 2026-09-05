from stackops.utils.cloud import rclone as rclone_utils
from stackops.utils.cloud.defaults import CloudConfig
from stackops.utils.cloud.encryption import EncryptionModeChoice


def main(
    source: str,
    target: str,
    transfers: int,
    root: str,
    pwd: str | None,
    encryption: EncryptionModeChoice | None,
    zip_: bool,
    bisync: bool,
    resync: bool,
    delete: bool,
    verbose: bool,
) -> None:
    from stackops.scripts.python.helpers.helpers_cloud.cloud_path_resolver import parse_cloud_source_target
    from stackops.utils.cloud.default_remote import DefaultRcloneRemoteConfigError

    from rich.console import Console
    from rich.panel import Panel
    console = Console()

    title = "☁️  Cloud Sync Utility"
    console.print(Panel(title, title_align="left", border_style="blue"))

    if resync and not bisync:
        raise ValueError("--resync requires --bisync.")

    unsupported_options: list[str] = []
    if pwd is not None:
        unsupported_options.append("--password")
    if encryption is not None:
        unsupported_options.append("--encryption")
    if zip_:
        unsupported_options.append("--zip")
    if unsupported_options:
        raise ValueError(
            f"cloud sync does not support {', '.join(unsupported_options)} because incremental sync cannot stage ZIP or GPG artifacts. "
            "Use cloud copy for compressed or encrypted transfers."
        )

    cloud_config_explicit = CloudConfig(
        cloud="",
        root=root,
        pwd=None,
        encryption=None,
        zip=False,
        rel2home=True,
        os_specific=False,
        overwrite=False,
        share=False,
    )

    try:
        _cloud, source, target = parse_cloud_source_target(
            cloud_config_explicit=cloud_config_explicit,
            source=source,
            target=target,
        )
    except DefaultRcloneRemoteConfigError as error:
        console.print(
            Panel(
                f"❌ {error}\n\nFor this command, replace a leading :path with REMOTE:path.",
                title="[bold red]Cloud Configuration Required[/bold red]",
                border_style="red",
            )
        )
        raise SystemExit(1) from None
    if bisync:
        title = "🔄 BI-DIRECTIONAL SYNC"
        source_line = f"Source: {source}"
        target_line = f"Target: {target}"
        console.print(Panel(f"{source_line}\n{target_line}", title=title, border_style="blue"))
        rclone_utils.bisync(
            source=source,
            target=target,
            transfers=transfers,
            resync=resync,
            delete_during=delete,
            remove_empty_dirs=False,
            show_command=verbose,
            show_progress=True,
        )
    else:
        title = "📤 ONE-WAY SYNC"
        source_line = f"Source: {source}"
        arrow_line = "↓"
        target_line = f"Target: {target}"
        console.print(Panel(f"{source_line}\n{arrow_line}\n{target_line}", title=title, border_style="blue"))
        rclone_utils.sync(
            source=source,
            target=target,
            transfers=transfers,
            delete=delete,
            show_command=verbose,
            show_progress=True,
        )
