"""
CC
"""

from pathlib import Path

import stackops.utils.path_compression as path_compression
from stackops.utils.io import (
    GpgCommandError,
    decrypt_file_asymmetric,
    decrypt_file_symmetric,
    encrypt_file_asymmetric,
    encrypt_file_symmetric,
)
from stackops.utils.encryption import EncryptionMode, parse_encryption_mode
from stackops.utils.path_core import delete_path
import stackops.utils.rclone_wrapper as rclone_wrapper
from stackops.utils.rclone import (
    RcloneCommandError,
    RcloneConfigError,
    ShareLinkOptions,
    ShareLinkTypeChoice,
    ShareScopeChoice,
    parse_share_link_type,
    parse_share_scope,
)
from stackops.utils.cloud_defaults import CloudConfig, read_default_cloud_config


defaults = read_default_cloud_config()


class ShareUrlDownloadError(RuntimeError):
    pass


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


def _resolve_encryption_settings(*, encrypt_requested: bool, encryption: str | None, pwd: str | None) -> tuple[bool, EncryptionMode | None]:
    encryption_mode = None if encryption is None else parse_encryption_mode(encryption, label="--encryption")
    if pwd is not None:
        if pwd == "":
            raise ValueError("--password must be non-empty.")
        if encryption_mode not in (None, "symmetric"):
            raise ValueError("--password can only be used with --encryption symmetric.")
        return True, "symmetric"
    if not encrypt_requested:
        if encryption_mode is not None:
            raise ValueError("--encryption can only be used when --encrypt is set.")
        return False, None
    if encryption_mode is None:
        raise ValueError("--encrypt requires --encryption symmetric or --encryption asymmetric.")
    return True, encryption_mode


def _resolve_share_options(*, share_scope: ShareScopeChoice | None, share_type: ShareLinkTypeChoice | None) -> ShareLinkOptions | None:
    if share_scope is None and share_type is None:
        return None
    scope = None if share_scope is None else parse_share_scope(share_scope, label="--share-scope")
    link_type = None if share_type is None else parse_share_link_type(share_type, label="--share-type")
    return ShareLinkOptions(scope=scope, link_type=link_type)


def _require_symmetric_password(pwd: str | None) -> str:
    if pwd is not None:
        return pwd
    import getpass

    return getpass.getpass(prompt="🔑 Enter symmetric GPG encryption password: ")


def _prepare_upload_path(
    *,
    local_path: Path,
    zip_requested: bool,
    encrypt_requested: bool,
    encryption_mode: EncryptionMode | None,
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
        if encryption_mode == "asymmetric":
            upload_path = encrypt_file_asymmetric(file_path=upload_path)
        elif encryption_mode == "symmetric":
            upload_path = encrypt_file_symmetric(file_path=upload_path, pwd=_require_symmetric_password(pwd))
        else:
            raise ValueError("Encryption mode is required when encryption is enabled.")
        temp_paths.append(upload_path)
    return upload_path, temp_paths


def _finalize_download_path(
    *,
    download_path: Path,
    zip_requested: bool,
    encrypt_requested: bool,
    encryption_mode: EncryptionMode | None,
    pwd: str | None,
    overwrite: bool,
) -> Path:
    local_path = download_path
    if encrypt_requested:
        from rich.console import Console
        from rich.panel import Panel

        encrypted_path = local_path
        if encrypted_path.name.endswith(".gpg"):
            output_path = encrypted_path.with_name(encrypted_path.name.removesuffix(".gpg"))
        else:
            output_path = encrypted_path.with_name(f"decrypted_{encrypted_path.name}")
        decrypt_mode = "GPG password decryption" if encryption_mode == "symmetric" else "GPG private-key decryption"
        console = Console()
        console.print(
            Panel(
                f"🔓 DECRYPTING DOWNLOADED ARTIFACT\n📥 Encrypted file: {encrypted_path}\n📄 Output file: {output_path}\n🔐 Mode: {decrypt_mode}",
                title="[bold blue]Decrypt[/bold blue]",
                border_style="blue",
            )
        )
        if encryption_mode == "asymmetric":
            local_path = decrypt_file_asymmetric(file_path=encrypted_path)
        elif encryption_mode == "symmetric":
            local_path = decrypt_file_symmetric(file_path=encrypted_path, pwd=_require_symmetric_password(pwd))
        else:
            raise ValueError("Encryption mode is required when encryption is enabled.")
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


def _download_url_to_path(*, url: str, destination: Path) -> Path:
    from urllib.parse import urlparse

    import requests

    parsed_url = urlparse(url)
    if parsed_url.scheme not in {"http", "https"} or parsed_url.netloc == "":
        raise ShareUrlDownloadError("share_url must be a valid http(s) URL.")

    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with requests.get(url, allow_redirects=True, stream=True, timeout=60) as response:
            try:
                response.raise_for_status()
            except requests.HTTPError as error:
                status_code = error.response.status_code if error.response is not None else "unknown"
                raise ShareUrlDownloadError(f"HTTP download failed with status code {status_code}.") from error
            with destination.open("wb") as output:
                for chunk in response.iter_content(chunk_size=8192 * 40):
                    if chunk:
                        output.write(chunk)
    except requests.RequestException as error:
        raise ShareUrlDownloadError(f"HTTP download failed: {type(error).__name__}.") from error
    except OSError as error:
        raise ShareUrlDownloadError(f"Could not write downloaded file: {error}") from error
    return destination


def download_from_share_url(
    *,
    share_url: str,
    target_path: Path,
    zip_requested: bool,
    encrypt_requested: bool,
    encryption_mode: EncryptionMode | None,
    pwd: str | None,
    overwrite: bool,
) -> Path:
    if encrypt_requested and encryption_mode is None:
        raise ValueError("Encryption mode is required when encryption is enabled.")
    direct_download_url = rclone_wrapper.google_drive_direct_download_url(share_url=share_url)
    download_url = share_url if direct_download_url is None else direct_download_url
    target_path_resolved = target_path.expanduser().absolute()
    download_path = _artifact_path(
        local_path=target_path_resolved,
        zip_requested=zip_requested,
        encrypt_requested=encrypt_requested,
    )
    _download_url_to_path(url=download_url, destination=download_path)
    return _finalize_download_path(
        download_path=download_path,
        zip_requested=zip_requested,
        encrypt_requested=encrypt_requested,
        encryption_mode=encryption_mode,
        pwd=pwd,
        overwrite=overwrite,
    )


def _split_remote_spec(value: str) -> tuple[str, str] | None:
    if ":" not in value or (len(value) > 1 and value[1] == ":"):
        return None
    cloud_name, remote_value = value.split(":", 1)
    return cloud_name, remote_value


def _strip_artifact_suffixes(remote_path: Path, *, zip_requested: bool, encrypt_requested: bool) -> str:
    remote_value = remote_path.as_posix()
    if encrypt_requested and remote_value.endswith(".gpg"):
        remote_value = remote_value.removesuffix(".gpg")
    if zip_requested and remote_value.endswith(".zip"):
        remote_value = remote_value.removesuffix(".zip")
    return remote_value


def _record_upload(
    *,
    source_path: Path,
    original_target: str,
    cloud: str,
    remote_path: Path,
    share_url: str | None,
    zip_requested: bool,
    encrypt_requested: bool,
    encryption_mode: EncryptionMode | None,
    rel2home: bool,
    record_group: str,
    record_name: str,
    record_os: str,
    expand_symbol: str,
) -> tuple[Path, str, bool]:
    from stackops.scripts.python.helpers.helpers_devops.backup_registration import register_backup_entry

    original_target_parts = _split_remote_spec(original_target)
    if original_target_parts is not None and original_target_parts[1] == expand_symbol:
        path_cloud = f"{cloud}:{expand_symbol}"
    else:
        remote_value = _strip_artifact_suffixes(
            remote_path,
            zip_requested=zip_requested,
            encrypt_requested=encrypt_requested,
        )
        path_cloud = f"{cloud}:{remote_value}"
    return register_backup_entry(
        path_local=source_path.as_posix(),
        group=record_group,
        entry_name=record_name,
        path_cloud=path_cloud,
        share_url=share_url,
        zip_=zip_requested,
        encrypt=encrypt_requested,
        encryption=encryption_mode,
        password=None,
        rel2home=rel2home,
        os=record_os,
    )


def _resolve_record_name(record_name: str | None) -> str | None:
    if record_name is None:
        return None
    normalized_record_name = record_name.strip()
    if normalized_record_name == "":
        raise ValueError("--record-name must be non-empty.")
    return normalized_record_name


def main(
    source: str,
    target: str,
    overwrite: bool,
    share_scope: ShareScopeChoice | None,
    share_type: ShareLinkTypeChoice | None,
    record_group: str,
    record_name: str | None,
    record_os: str,
    rel2home: bool,
    root: str,
    pwd: str | None,
    encrypt: bool,
    encryption: str | None,
    zip_: bool,
    os_specific: bool,
) -> None:
    """📤 Upload or 📥 Download files/folders to/from cloud storage services like Google Drive, Dropbox, OneDrive, etc."""
    from rich.console import Console
    from rich.panel import Panel
    from stackops.scripts.python.helpers.helpers_cloud.cloud_path_resolver import ES, parse_cloud_source_target
    console = Console()
    console.print(Panel("☁️  Cloud Copy Utility", title="[bold blue]Cloud Copy[/bold blue]", border_style="blue", width=152))
    original_target = target

    try:
        encrypt_effective, encryption_mode = _resolve_encryption_settings(encrypt_requested=encrypt, encryption=encryption, pwd=pwd)
        share_options = _resolve_share_options(share_scope=share_scope, share_type=share_type)
        resolved_record_name = _resolve_record_name(record_name)
    except ValueError as error:
        console.print(Panel(f"❌ ERROR: Invalid cloud copy configuration\n{error}", title="[bold red]Error[/bold red]", border_style="red", width=152))
        raise SystemExit(1) from None

    cloud_config_explicit = CloudConfig(
        cloud="",
        overwrite=overwrite,
        share=share_options is not None,
        rel2home=rel2home,
        root=root,
        pwd=pwd,
        encrypt=encrypt_effective,
        encryption=encryption_mode,
        zip=zip_,
        os_specific=os_specific,
    )

    console.print(Panel("🔍 Parsing source and target paths...", title="[bold blue]Info[/bold blue]", border_style="blue"))
    cloud, source, target = parse_cloud_source_target(
        cloud_config_explicit=cloud_config_explicit,
        source=source,
        target=target,
    )
    if cloud in source:
        if resolved_record_name is not None:
            console.print(Panel("❌ --record-name is only supported for uploads to cloud targets.", title="[bold red]Error[/bold red]", border_style="red", width=152))
            raise SystemExit(1)
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
                encryption_mode=cloud_config_explicit["encryption"],
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
                encryption_mode=cloud_config_explicit["encryption"],
                pwd=cloud_config_explicit["pwd"],
            )
            share_url = rclone_wrapper.to_cloud(
                local_path=upload_path,
                cloud=cloud,
                remote_path=remote_path,
                share=cloud_config_explicit["share"],
                share_options=share_options,
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
        except RcloneConfigError as error:
            console.print(
                Panel(
                    f"☁️  Cloud: {cloud}\n📂 Source: {source}\n🎯 Target: {target.replace(cloud + ':', '')}\n\n{error}",
                    title="[bold red]Rclone Config Error[/bold red]",
                    border_style="red",
                    width=152,
                )
            )
            raise SystemExit(1) from None
        finally:
            _delete_temp_paths(temp_paths)
        console.print(Panel("✅ Upload completed successfully", title="[bold green]Success[/bold green]", border_style="green", width=152))

        if cloud_config_explicit["share"] and share_url is None:
            raise RuntimeError("Share was requested but rclone did not return a share URL.")
        if resolved_record_name is not None:
            backup_path, entry_name, replaced = _record_upload(
                source_path=source_path,
                original_target=original_target,
                cloud=cloud,
                remote_path=remote_path,
                share_url=share_url,
                zip_requested=cloud_config_explicit["zip"],
                encrypt_requested=cloud_config_explicit["encrypt"],
                encryption_mode=cloud_config_explicit["encryption"],
                rel2home=cloud_config_explicit["rel2home"],
                record_group=record_group,
                record_name=resolved_record_name,
                record_os=record_os,
                expand_symbol=ES,
            )
            action = "Updated" if replaced else "Added"
            if share_url is None:
                console.print(Panel(f"📝 RECORDED UPLOAD\n📝 {action} backup entry: {entry_name}\n📄 Data file: {backup_path}", title="[bold blue]Record[/bold blue]", border_style="blue", width=152))
            else:
                console.print(Panel(f"🔗 SHARE URL GENERATED\n📝 {action} backup entry: {entry_name}\n📄 Data file: {backup_path}\n🌍 {share_url}", title="[bold blue]Share[/bold blue]", border_style="blue", width=152))
        elif cloud_config_explicit["share"]:
            if share_url is None:
                raise RuntimeError("Share was requested but rclone did not return a share URL.")
            console.print(Panel(f"🔗 SHARE URL GENERATED\n🌍 {share_url}", title="[bold blue]Share[/bold blue]", border_style="blue", width=152))
    else:
        console.print(Panel(f"❌ ERROR: Cloud '{cloud}' not found in source or target", title="[bold red]Error[/bold red]", border_style="red", width=152))
        raise SystemExit(1)
