"""Cloud management commands - lazy loading subcommands."""

from typing import Annotated, Literal

import typer

from stackops.utils.cli_utils.alias_markers import apply_alias_markers
from stackops.utils.cloud.defaults import read_default_cloud_config
from stackops.utils.cloud.encryption import EncryptionModeChoice
from stackops.utils.cloud.rclone import ShareLinkTypeChoice, ShareScopeChoice


defaults = read_default_cloud_config()


def sync(
    source: Annotated[str, typer.Argument(help="source")],
    target: Annotated[str, typer.Argument(help="target")],
    transfers: Annotated[int, typer.Option("--transfers", "-t", help="Number of threads in syncing.")] = 10,
    root: Annotated[str, typer.Option("--root", "-R", help="Remote root.")] = defaults["root"],
    pwd: Annotated[str | None, typer.Option("--pwd", "-P", help="Symmetric GPG encryption password. Requires --encryption symmetric.")] = defaults["pwd"],
    encryption: Annotated[
        EncryptionModeChoice | None,
        typer.Option("--encryption", "-e", help="Encryption mode: symmetric/s or asymmetric/a. Omit for plaintext."),
    ] = defaults["encryption"],
    zip_: Annotated[bool, typer.Option("--zip", "-z", help="unzip after receiving.")] = defaults["zip"],
    bisync: Annotated[bool, typer.Option("--bisync", "-b", help="Bidirectional sync.")] = False,
    resync: Annotated[bool, typer.Option("--resync", "-r", help="Initialize or recover --bisync state. Omit for normal bidirectional syncs.")] = False,
    delete: Annotated[
        bool,
        typer.Option("--delete", "-D", help="Delete destination-only files during one-way sync. Bisync always propagates deletions; this flag changes their timing."),
    ] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Show the rclone command being executed.")] = False,
) -> None:
    """🔄 Synchronize files/folders between local and cloud storage."""
    from stackops.scripts.python.helpers.helpers_cloud.cloud_sync import main as sync_main
    from stackops.utils.cloud.rclone import RcloneCommandError

    try:
        sync_main(
            source=source,
            target=target,
            transfers=transfers,
            root=root,
            pwd=pwd,
            encryption=encryption,
            zip_=zip_,
            bisync=bisync,
            resync=resync,
            delete=delete,
            verbose=verbose,
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except RcloneCommandError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=error.returncode) from error
    except RuntimeError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error


def copy(
    source: Annotated[str, typer.Argument(help="📂 file/folder path to be taken from here.")],
    target: Annotated[str, typer.Argument(help="🎯 file/folder path to be be sent to here.")],
    transfers: Annotated[int, typer.Option("--transfers", "-T", help="🔀 Number of concurrent file transfers.")] = 32,
    overwrite: Annotated[bool, typer.Option("--overwrite", "-o", help="📝 Overwrite existing file.")] = defaults["overwrite"],
    share_scope: Annotated[ShareScopeChoice | None, typer.Option("--share-scope", "-s", help="🔗 Share link scope: anonymous/a or organization/o.")] = None,
    share_type: Annotated[ShareLinkTypeChoice | None, typer.Option("--share-type", "-t", help="🔗 Share link type: view/v, edit/e, or embed/m.")] = None,
    record_group: Annotated[str, typer.Option("--record-group", "-g", help="🗂 Group name for mapper/data.yaml. Used when --record-name is passed.")] = "default",
    record_name: Annotated[str | None, typer.Option("--record-name", "-n", help="🏷 Record the upload in mapper/data.yaml with this entry name.")] = None,
    record_os: Annotated[str, typer.Option("--record-os", "-F", help="💻 OS filter for recorded uploads. Comma-separated: linux,darwin,windows. Defaults to all.")] = "linux,darwin,windows",
    rel2home: Annotated[bool, typer.Option("--relative2home", "-r", help="🏠 Relative to `myhome` folder")] = defaults["rel2home"],
    root: Annotated[str, typer.Option("--root", "-R", help="🌳 Remote root.")] = defaults["root"],
    pwd: Annotated[str | None, typer.Option("--password", "-p", help="🔒 Symmetric GPG encryption password. Requires --encryption symmetric.")] = defaults["pwd"],
    password_name: Annotated[
        str | None,
        typer.Option("--password-name", "-P", help="🔐 Exact StackOps secrets login name containing PASSWORD. Requires --encryption symmetric."),
    ] = None,
    encryption: Annotated[
        EncryptionModeChoice | None,
        typer.Option("--encryption", "-e", help="🔐 Encryption mode: symmetric/s or asymmetric/a. Omit for plaintext."),
    ] = defaults["encryption"],
    zip_: Annotated[bool, typer.Option("--zip", "-z", help="📦 unzip after receiving.")] = defaults["zip"],
    os_specific: Annotated[bool, typer.Option("--os-specific", "-O", help="💻 choose path specific for this OS.")] = defaults["os_specific"],
) -> None:
    """📤 Upload or 📥 Download files/folders to/from cloud storage services."""
    from stackops.scripts.python.helpers.helpers_cloud.cloud_copy import main as copy_main

    copy_main(
        source=source,
        target=target,
        transfers=transfers,
        overwrite=overwrite,
        share_scope=share_scope,
        share_type=share_type,
        record_group=record_group,
        record_name=record_name,
        record_os=record_os,
        rel2home=rel2home,
        root=root,
        pwd=pwd,
        password_name=password_name,
        encryption=encryption,
        zip_=zip_,
        os_specific=os_specific,
    )


def mount(
    clouds: Annotated[list[str] | None, typer.Argument(help="cloud remotes to mount, omit for interactive selection")] = None,
    destination: Annotated[str | None, typer.Option("--destination", "-d", help="destination to mount")] = None,
    network: Annotated[str | None, typer.Option("--network", "-n", help="Windows network mount target, for example X:")] = None,
    backend: Annotated[Literal["tmux", "t", "auto", "a"], typer.Option("--backend", "-b", help="terminal backend for Linux/macOS")] = "tmux",
) -> None:
    """🔗 Mount cloud storage services as local drives."""
    from stackops.scripts.python.helpers.helpers_cloud.cloud_mount import mount as mount_main
    mount_main(clouds=clouds, destination=destination, network=network, backend=backend)


def ftpx(
    source: Annotated[str, typer.Argument(help="Source path (machine:path)")],
    target: Annotated[str, typer.Argument(help="Target path (machine:path)")],
    recursive: Annotated[bool, typer.Option("--recursive", "-r", help="Send recursively.")] = False,
    zip_first: Annotated[bool, typer.Option("--zip-first", "-z", help="Zip before sending.")] = False,
    cloud: Annotated[bool, typer.Option("--cloud", "-c", help="Transfer through the cloud.")] = False,
    overwrite_existing: Annotated[bool, typer.Option("--overwrite-existing", "-o", help="Overwrite existing files on remote when sending from local to remote.")] = False,
) -> None:
    """📦 File transfer utility through SSH."""
    from stackops.scripts.python.ftpx import ftpx as ftpx_impl
    ftpx_impl(source=source, target=target, recursive=recursive, zip_first=zip_first, cloud=cloud, overwrite_existing=overwrite_existing)


def get_app() -> typer.Typer:
    from stackops.utils.cloud.onedrive.cli import get_app as get_onedrive_app

    app = typer.Typer(add_completion=False, no_args_is_help=True, help="☁ Cloud management commands")

    app.command(name="sync", no_args_is_help=True, short_help="🔄 <s> Synchronize files/folders between local and cloud storage.")(sync)
    app.command(name="s", no_args_is_help=True, hidden=True)(sync)

    app.command(name="copy", no_args_is_help=True, short_help="📤 <c> Upload or 📥 Download files/folders to/from cloud storage.")(copy)
    app.command(name="c", no_args_is_help=True, hidden=True)(copy)

    app.command(name="mount", short_help="🔗 <m> Mount cloud storage services as local drives.")(mount)
    app.command(name="m", hidden=True)(mount)

    app.command(name="ftpx", no_args_is_help=True, short_help="📦 <f> File transfer utility through SSH.")(ftpx)
    app.command(name="f", no_args_is_help=True, hidden=True)(ftpx)

    app.add_typer(get_onedrive_app(), name="onedrive", help="☁ <o> Access OneDrive through Microsoft Graph.")
    app.add_typer(get_onedrive_app(), name="o", help="Access OneDrive through Microsoft Graph.", hidden=True)

    return apply_alias_markers(app)


def main() -> None:
    app = get_app()
    app()


if __name__ == "__main__":
    main()
