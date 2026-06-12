"""Cloud management commands - lazy loading subcommands."""

import typer
from typing import Annotated, Literal
from stackops.profile.dotfiles_mapper import DEFAULT_OS_FILTER
from stackops.utils.cloud.defaults import read_default_cloud_config
from stackops.utils.encryption import EncryptionModeChoice
from stackops.utils.rclone import ShareLinkTypeChoice, ShareScopeChoice


defaults = read_default_cloud_config()


def sync(
    source: Annotated[str, typer.Argument(help="source")],
    target: Annotated[str, typer.Argument(help="target")],
    transfers: Annotated[int, typer.Option("--transfers", "-t", help="Number of threads in syncing.")] = 10,
    root: Annotated[str, typer.Option("--root", "-R", help="Remote root.")] = defaults["root"],
    pwd: Annotated[str | None, typer.Option("--pwd", "-P", help="Symmetric GPG encryption password used when --encrypt is set.")] = defaults["pwd"],
    encrypt: Annotated[bool, typer.Option("--encrypt", "-e", help="Decrypt after receiving.")] = defaults["encrypt"],
    zip_: Annotated[bool, typer.Option("--zip", "-z", help="unzip after receiving.")] = defaults["zip"],
    bisync: Annotated[bool, typer.Option("--bisync", "-b", help="Bidirectional sync.")] = False,
    delete: Annotated[bool, typer.Option("--delete", "-D", help="Delete files in remote that are not in local.")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Verbosity of mprocs to show details of syncing.")] = False,
) -> None:
    """🔄 Synchronize files/folders between local and cloud storage."""
    from stackops.scripts.python.helpers.helpers_cloud.cloud_sync import main as sync_main
    sync_main(source=source, target=target, transfers=transfers, root=root, pwd=pwd, encrypt=encrypt, zip_=zip_, bisync=bisync, delete=delete, verbose=verbose)


def copy(
    source: Annotated[str, typer.Argument(help="📂 file/folder path to be taken from here.")],
    target: Annotated[str, typer.Argument(help="🎯 file/folder path to be be sent to here.")],
    overwrite: Annotated[bool, typer.Option("--overwrite", "-o", help="📝 Overwrite existing file.")] = defaults["overwrite"],
    share_scope: Annotated[ShareScopeChoice | None, typer.Option("--share-scope", "-s", help="🔗 Share link scope: anonymous/a or organization/o.")] = None,
    share_type: Annotated[ShareLinkTypeChoice | None, typer.Option("--share-type", "-t", help="🔗 Share link type: view/v, edit/e, or embed/m.")] = None,
    record_group: Annotated[str, typer.Option("--record-group", "-g", help="🗂 Group name for mapper/data.yaml. Used when --record-name is passed.")] = "default",
    record_name: Annotated[str | None, typer.Option("--record-name", "-n", help="🏷 Record the upload in mapper/data.yaml with this entry name.")] = None,
    record_os: Annotated[str, typer.Option("--record-os", "-F", help="💻 OS filter for recorded uploads. Comma-separated: linux,darwin,windows. Defaults to all.")] = DEFAULT_OS_FILTER,
    rel2home: Annotated[bool, typer.Option("--relative2home", "-r", help="🏠 Relative to `myhome` folder")] = defaults["rel2home"],
    root: Annotated[str, typer.Option("--root", "-R", help="🌳 Remote root.")] = defaults["root"],
    pwd: Annotated[str | None, typer.Option("--password", "-p", help="🔒 Symmetric GPG encryption password. Implies --encrypt --encryption symmetric.")] = defaults["pwd"],
    encrypt: Annotated[bool, typer.Option("--encrypt", "-e", help="🔐 Encrypt before sending.")] = defaults["encrypt"],
    encryption: Annotated[EncryptionModeChoice | None, typer.Option("--encryption", "-E", help="🔐 Encryption mode when --encrypt is set: symmetric/s or asymmetric/a.")] = defaults["encryption"],
    zip_: Annotated[bool, typer.Option("--zip", "-z", help="📦 unzip after receiving.")] = defaults["zip"],
    os_specific: Annotated[bool, typer.Option("--os-specific", "-O", help="💻 choose path specific for this OS.")] = defaults["os_specific"],
) -> None:
    """📤 Upload or 📥 Download files/folders to/from cloud storage services."""
    from stackops.scripts.python.helpers.helpers_cloud.cloud_copy import main as copy_main

    copy_main(
        source=source,
        target=target,
        overwrite=overwrite,
        share_scope=share_scope,
        share_type=share_type,
        record_group=record_group,
        record_name=record_name,
        record_os=record_os,
        rel2home=rel2home,
        root=root,
        pwd=pwd,
        encrypt=encrypt,
        encryption=encryption,
        zip_=zip_,
        os_specific=os_specific,
    )


def mount(
    cloud: Annotated[str | None, typer.Option(..., "--cloud", "-c", help="cloud to mount.")] = None,
    destination: Annotated[str | None, typer.Option(..., "--destination", "-d", help="destination to mount")] = None,
    network: Annotated[str | None, typer.Option(..., "--network", "-n", help="Windows network mount target, for example X:")] = None,
    backend: Annotated[Literal["zellij", "z", "tmux", "t", "auto", "a"], typer.Option("--backend", "-b", help="terminal backend for Linux/macOS")] = "tmux",
    interactive: Annotated[bool, typer.Option("--no-interactive", "-I", help="Require --cloud instead of choosing interactively from config.")] = True,

) -> None:
    """🔗 Mount cloud storage services as local drives."""
    from stackops.scripts.python.helpers.helpers_cloud.cloud_mount import mount as mount_main
    mount_main(cloud=cloud, destination=destination, network=network, backend=backend, interactive=interactive)


def ftpx(
    source: Annotated[str, typer.Argument(help="Source path (machine:path)")],
    target: Annotated[str, typer.Argument(help="Target path (machine:path)")],
    recursive: Annotated[bool, typer.Option("--recursive", "-r", help="Send recursively.")] = False,
    zipFirst: Annotated[bool, typer.Option("--zipFirst", "-z", help="Zip before sending.")] = False,
    cloud: Annotated[bool, typer.Option("--cloud", "-c", help="Transfer through the cloud.")] = False,
    overwrite_existing: Annotated[bool, typer.Option("--overwrite-existing", "-o", help="Overwrite existing files on remote when sending from local to remote.")] = False,
) -> None:
    """📦 File transfer utility through SSH."""
    from stackops.scripts.python.ftpx import ftpx as ftpx_impl
    ftpx_impl(source=source, target=target, recursive=recursive, zipFirst=zipFirst, cloud=cloud, overwrite_existing=overwrite_existing)


def get_app() -> typer.Typer:
    app = typer.Typer(add_completion=False, no_args_is_help=True, help="☁ Cloud management commands")

    app.command(name="sync", no_args_is_help=True, short_help="🔄 <s> Synchronize files/folders between local and cloud storage.")(sync)
    app.command(name="s", no_args_is_help=True, hidden=True)(sync)

    app.command(name="copy", no_args_is_help=True, short_help="📤 <c> Upload or 📥 Download files/folders to/from cloud storage.")(copy)
    app.command(name="c", no_args_is_help=True, hidden=True)(copy)

    app.command(name="mount", no_args_is_help=True, short_help="🔗 <m> Mount cloud storage services as local drives.")(mount)
    app.command(name="m", no_args_is_help=True, hidden=True)(mount)

    app.command(name="ftpx", no_args_is_help=True, short_help="📦 <f> File transfer utility through SSH.")(ftpx)
    app.command(name="f", no_args_is_help=True, hidden=True)(ftpx)

    return app


def main() -> None:
    app = get_app()
    app()


if __name__ == "__main__":
    main()
