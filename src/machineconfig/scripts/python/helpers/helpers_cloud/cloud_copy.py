"""
CC
"""

from pathlib import Path

import machineconfig.utils.path_compression as path_compression
import machineconfig.utils.path_core as path_core
from machineconfig.utils.io import (
    GpgCommandError,
    decrypt_file_asymmetric,
    decrypt_file_symmetric,
    encrypt_file_asymmetric,
    encrypt_file_symmetric,
)
from machineconfig.utils.path_core import delete_path
import machineconfig.utils.rclone_wrapper as rclone_wrapper
from machineconfig.utils.rclone import RcloneCommandError
from machineconfig.utils.ve import CLOUD, read_default_cloud_config

from tenacity import retry, stop_after_attempt, wait_chain, wait_fixed


defaults = read_default_cloud_config()


def _artifact_path(local_path: Path, zip_requested: bool, encrypt_requested: bool) -> Path:
    suffix = ""
    if zip_requested:
        suffix += ".zip"
    if encrypt_requested:
        suffix += ".gpg"
    return Path(f"{local_path}{suffix}")


def _delete_temp_paths(paths: list[Path]) -> None:
    for temp_path in paths:
        delete_path(temp_path, verbose=False)


def _prepare_upload_path(
    *,
    local_path: Path,
    zip_requested: bool,
    encrypt_requested: bool,
    pwd: str | None,
) -> tuple[Path, list[Path]]:
    upload_path = local_path.expanduser().absolute()
    temp_paths: list[Path] = []
    if zip_requested:
        upload_path = path_compression.zip_path(
            upload_path,
            path=None,
            folder=None,
            name=None,
            arcname=None,
            inplace=False,
            verbose=True,
            content=False,
            orig=False,
            mode="w",
        )
        temp_paths.append(upload_path)
    if encrypt_requested:
        if pwd is None:
            upload_path = encrypt_file_asymmetric(file_path=upload_path)
        else:
            upload_path = encrypt_file_symmetric(file_path=upload_path, pwd=pwd)
        temp_paths.append(upload_path)
    return upload_path, temp_paths


def _finalize_download_path(
    *,
    download_path: Path,
    zip_requested: bool,
    encrypt_requested: bool,
    pwd: str | None,
    overwrite: bool,
) -> Path:
    local_path = download_path
    if encrypt_requested:
        encrypted_path = local_path
        if pwd is None:
            local_path = decrypt_file_asymmetric(file_path=encrypted_path)
        else:
            local_path = decrypt_file_symmetric(file_path=encrypted_path, pwd=pwd)
        delete_path(encrypted_path, verbose=False)
    if zip_requested:
        local_path = path_compression.unzip_path(
            local_path,
            folder=None,
            path=None,
            name=None,
            verbose=True,
            content=True,
            inplace=True,
            overwrite=overwrite,
            orig=False,
            pwd=None,
            tmp=False,
            pattern=None,
            merge=False,
        )
    return local_path


@retry(stop=stop_after_attempt(3), wait=wait_chain(wait_fixed(1), wait_fixed(4), wait_fixed(9)))
def get_securely_shared_file(url: str | None, folder: str | None) -> None:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress
    import getpass
    import os
    from machineconfig.utils.io import GpgCommandError, decrypt_file_symmetric
    console = Console()
    console.print(Panel("🚀 Secure File Downloader", title="[bold blue]Downloader[/bold blue]", border_style="blue"))
    folder_obj = Path.cwd() if folder is None else Path(folder).expanduser()
    print(f"📂 Target folder: {folder_obj}")

    if os.environ.get("DECRYPTION_PASSWORD") is not None:
        print("🔑 Using password from environment variables")
        pwd = str(os.environ.get("DECRYPTION_PASSWORD"))
    else:
        pwd = getpass.getpass(prompt="🔑 Enter decryption password: ")

    if url is None:
        if os.environ.get("SHARE_URL") is not None:
            url = os.environ.get("SHARE_URL")
            assert url is not None
            print("🔗 Using URL from environment variables")
        else:
            url = input("🔗 Enter share URL: ")

    console.print(Panel("📡 Downloading from URL...", title="[bold blue]Download[/bold blue]", border_style="blue"))
    with Progress(transient=True) as progress:
        _task = progress.add_task("Downloading... ", total=None)
        url_obj = path_core.download(url, folder=folder_obj)

    console.print(Panel(f"📥 Downloaded file: {url_obj}", title="[bold green]Success[/bold green]", border_style="green"))

    console.print(Panel("🔐 Decrypting and extracting...", title="[bold blue]Processing[/bold blue]", border_style="blue"))
    with Progress(transient=True) as progress:
        _task = progress.add_task("Decrypting... ", total=None)
        tmp_folder = path_core.tmpdir(prefix="tmp_unzip")
        try:
            try:
                decrypted_path = Path(decrypt_file_symmetric(file_path=url_obj, pwd=pwd))
            except GpgCommandError as error:
                console.print(
                    Panel(
                        f"URL: {url_obj}\n📂 Target folder: {folder_obj}\n\n{error}",
                        title="[bold red]GPG Error[/bold red]",
                        border_style="red",
                    )
                )
                raise SystemExit(1) from None
            delete_path(url_obj, verbose=False)
            res = path_compression.unzip_path(
                decrypted_path,
                folder=tmp_folder,
                path=None,
                name=None,
                verbose=True,
                content=False,
                inplace=True,
                overwrite=False,
                orig=False,
                pwd=None,
                tmp=False,
                pattern=None,
                merge=False,
            )
            for x in res.glob("*"):
                path_core.move(x, folder=folder_obj, overwrite=True)
        finally:
            # Clean up temporary folder
            if tmp_folder.exists():
                delete_path(tmp_folder, verbose=False)

def main(
    source: str,
    target: str,
    overwrite: bool,
    share: bool,
    rel2home: bool,
    root: str,
    key: str | None,
    pwd: str | None,
    encrypt: bool,
    zip_: bool,
    os_specific: bool,
    config: str | None,
) -> None:
    """📤 Upload or 📥 Download files/folders to/from cloud storage services like Google Drive, Dropbox, OneDrive, etc."""
    from rich.console import Console
    from rich.panel import Panel
    from machineconfig.scripts.python.helpers.helpers_cloud.helpers2 import parse_cloud_source_target
    console = Console()
    console.print(Panel("☁️  Cloud Copy Utility", title="[bold blue]Cloud Copy[/bold blue]", border_style="blue", width=152))
    cloud_config_explicit = CLOUD(
        cloud="",
        overwrite=overwrite,
        share=share,
        rel2home=rel2home,
        root=root,
        key=key,
        pwd=pwd,
        encrypt=encrypt,
        zip=zip_,
        os_specific=os_specific,
    )

    if config == "ss" and (source.startswith("http") or source.startswith("bit.ly")):
        console.print(Panel("🔒 Detected secure share link", title="[bold yellow]Warning[/bold yellow]", border_style="yellow"))
        if source.startswith("https://drive.google.com/open?id="):
            file_id = source.split("https://drive.google.com/open?id=")[1]
            if file_id:  # Ensure we actually extracted an ID
                source = f"https://drive.google.com/uc?export=download&id={file_id}"
                print("🔄 Converting Google Drive link to direct download URL")
            else:
                console.print(Panel("❌ Invalid Google Drive link format", title="[bold red]Error[/bold red]", border_style="red"))
                raise SystemExit(1)
        get_securely_shared_file(url=source, folder=target)
        return

    console.print(Panel("🔍 Parsing source and target paths...", title="[bold blue]Info[/bold blue]", border_style="blue"))
    cloud, source, target = parse_cloud_source_target(
        cloud_config_explicit=cloud_config_explicit,
        cloud_config_defaults=defaults,
        cloud_config_name=config,
        source=source,
        target=target,
    )
    if cloud_config_explicit["key"] is not None:
        console.print(Panel("❌ Key-based encryption is not supported yet", title="[bold red]Error[/bold red]", border_style="red"))
        raise SystemExit(1)
    if cloud in source:
        console.print(Panel(f"📥 DOWNLOADING FROM CLOUD\n☁️  Cloud: {cloud}\n📂 Source: {source.replace(cloud + ':', '')}\n🎯 Target: {target}", title="[bold blue]Download[/bold blue]", border_style="blue", width=152))
        target_path = Path(target).expanduser().absolute()
        remote_path = Path(source.replace(cloud + ":", ""))
        download_path = _artifact_path(
            local_path=target_path,
            zip_requested=cloud_config_explicit["zip"],
            encrypt_requested=cloud_config_explicit["encrypt"],
        )
        try:
            rclone_wrapper.from_cloud(
                local_path=download_path,
                cloud=cloud,
                remote_path=remote_path,
                transfers=10,
                verbose=True,
            )
            _finalize_download_path(
                download_path=download_path,
                zip_requested=cloud_config_explicit["zip"],
                encrypt_requested=cloud_config_explicit["encrypt"],
                pwd=cloud_config_explicit["pwd"],
                overwrite=cloud_config_explicit["overwrite"],
            )
        except GpgCommandError as error:
            console.print(
                Panel(
                    f"☁️  Cloud: {cloud}\n📂 Source: {source.replace(cloud + ':', '')}\n🎯 Target: {target}\n\n{error}",
                    title="[bold red]GPG Error[/bold red]",
                    border_style="red",
                    width=152,
                )
            )
            raise SystemExit(1) from None
        except RcloneCommandError as error:
            console.print(
                Panel(
                    f"☁️  Cloud: {cloud}\n📂 Source: {source.replace(cloud + ':', '')}\n🎯 Target: {target}\n\n{error}",
                    title="[bold red]Rclone Error[/bold red]",
                    border_style="red",
                    width=152,
                )
            )
            raise SystemExit(1) from None
        console.print(Panel("✅ Download completed successfully", title="[bold green]Success[/bold green]", border_style="green", width=152))

    elif cloud in target:
        console.print(Panel(f"📤 UPLOADING TO CLOUD\n☁️  Cloud: {cloud}\n📂 Source: {source}\n🎯 Target: {target.replace(cloud + ':', '')}", title="[bold blue]Upload[/bold blue]", border_style="blue", width=152))
        source_path = Path(source).expanduser().absolute()
        remote_path = Path(target.replace(cloud + ":", ""))
        temp_paths: list[Path] = []
        share_url: str | None = None
        try:
            upload_path, temp_paths = _prepare_upload_path(
                local_path=source_path,
                zip_requested=cloud_config_explicit["zip"],
                encrypt_requested=cloud_config_explicit["encrypt"],
                pwd=cloud_config_explicit["pwd"],
            )
            share_url = rclone_wrapper.to_cloud(
                local_path=upload_path,
                cloud=cloud,
                remote_path=remote_path,
                share=cloud_config_explicit["share"],
                verbose=True,
                transfers=10,
            )
        except GpgCommandError as error:
            console.print(
                Panel(
                    f"☁️  Cloud: {cloud}\n📂 Source: {source}\n🎯 Target: {target.replace(cloud + ':', '')}\n\n{error}",
                    title="[bold red]GPG Error[/bold red]",
                    border_style="red",
                    width=152,
                )
            )
            raise SystemExit(1) from None
        except RcloneCommandError as error:
            console.print(
                Panel(
                    f"☁️  Cloud: {cloud}\n📂 Source: {source}\n🎯 Target: {target.replace(cloud + ':', '')}\n\n{error}",
                    title="[bold red]Rclone Error[/bold red]",
                    border_style="red",
                    width=152,
                )
            )
            raise SystemExit(1) from None
        finally:
            _delete_temp_paths(temp_paths)
        console.print(Panel("✅ Upload completed successfully", title="[bold green]Success[/bold green]", border_style="green", width=152))

        if cloud_config_explicit["share"]:
            fname = f".share_url_{cloud}"
            if share_url is None:
                raise RuntimeError("Share was requested but rclone did not return a share URL.")
            if source_path.is_dir():
                share_url_path = source_path.joinpath(fname)
            else:
                share_url_path = source_path.with_suffix(fname)
            share_url_path.write_text(share_url, encoding="utf-8")
            console.print(Panel(f"🔗 SHARE URL GENERATED\n📝 URL file: {share_url_path}\n🌍 {share_url}", title="[bold blue]Share[/bold blue]", border_style="blue", width=152))
    else:
        console.print(Panel(f"❌ ERROR: Cloud '{cloud}' not found in source or target", title="[bold red]Error[/bold red]", border_style="red", width=152))
        raise SystemExit(1)
