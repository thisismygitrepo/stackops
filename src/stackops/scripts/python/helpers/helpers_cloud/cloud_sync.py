from stackops.utils.cloud.defaults import CloudConfig, read_default_cloud_config
from stackops.utils.cloud.encryption import EncryptionModeChoice


defaults = read_default_cloud_config()


def main(
    source: str,
    target: str,
    transfers: int,
    root: str,
    pwd: str | None,
    encryption: EncryptionModeChoice | None,
    zip_: bool,
    bisync: bool,
    delete: bool,
    verbose: bool,
) -> None:
    from stackops.scripts.python.helpers.helpers_cloud.cloud_path_resolver import parse_cloud_source_target
    from stackops.scripts.python.helpers.helpers_cloud.cloud_mount import get_mprocs_mount_txt
    from stackops.utils.cloud.default_remote import DefaultRcloneRemoteConfigError

    from rich.console import Console
    from rich.panel import Panel
    console = Console()

    title = "☁️  Cloud Sync Utility"
    console.print(Panel(title, title_align="left", border_style="blue"))

    unsupported_options: list[str] = []
    if pwd is not None:
        unsupported_options.append("--pwd")
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
        cloud, source, target = parse_cloud_source_target(
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
    # map short flags to long flags (-u -> --upload), for easier use in the script
    if bisync:
        title = "🔄 BI-DIRECTIONAL SYNC"
        source_line = f"Source: {source}"
        target_line = f"Target: {target}"
        console.print(Panel(f"{source_line}\n{target_line}", title=title, border_style="blue"))
        rclone_cmd = f"""rclone bisync '{source}' '{target}' --resync"""
    else:
        title = "📤 ONE-WAY SYNC"
        source_line = f"Source: {source}"
        arrow_line = "↓"
        target_line = f"Target: {target}"
        console.print(Panel(f"{source_line}\n{arrow_line}\n{target_line}", title=title, border_style="blue"))
        if delete:
            rclone_cmd = f'rclone sync -P "{source}" "{target}" --delete-during --transfers={transfers}'
        else:
            rclone_cmd = f'rclone sync -P "{source}" "{target}" --transfers={transfers}'

    rclone_cmd += f" --progress --transfers={transfers} --verbose"
    # rclone_cmd += f"  --vfs-cache-mode full"
    if delete:
        rclone_cmd += " --delete-during"

    if verbose:
        txt = get_mprocs_mount_txt(cloud=cloud, rclone_cmd=rclone_cmd, cloud_brand="Unknown")
    else:
        txt = f"""{rclone_cmd}"""

    title = "🚀 EXECUTING COMMAND"
    cmd_line = f"{rclone_cmd[:65]}..."
    console.print(Panel(f"{title}\n{cmd_line}", title="[bold blue]Command[/bold blue]", expand=False))

    # import subprocess
    # subprocess.run(txt, shell=True, check=True)
    from stackops.utils.code import run_shell_script
    run_shell_script(txt, display_script=True, clean_env=False)
