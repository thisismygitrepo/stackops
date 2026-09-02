from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import shutil
from tempfile import TemporaryDirectory
import zipfile

import stackops.utils.files.compression as path_compression
from stackops.utils.cloud.encryption import EncryptionMode
from stackops.utils.io import (
    decrypt_file_asymmetric,
    decrypt_file_symmetric,
    encrypt_file_asymmetric,
    encrypt_file_symmetric,
)


@dataclass(frozen=True)
class StagedDownload:
    artifact_path: Path
    staging_root: Path
    target_path: Path


def artifact_path(local_path: Path, *, zip_requested: bool, encryption_mode: EncryptionMode | None) -> Path:
    suffix = ".zip" if zip_requested else ""
    if encryption_mode is not None:
        suffix += ".gpg"
    return Path(f"{local_path}{suffix}")


def _symmetric_password(pwd: str | None) -> str:
    if pwd is not None:
        return pwd
    import getpass

    return getpass.getpass(prompt="🔑 Enter symmetric GPG encryption password: ")


@contextmanager
def prepared_upload_path(
    *,
    local_path: Path,
    zip_requested: bool,
    encryption_mode: EncryptionMode | None,
    pwd: str | None,
) -> Generator[Path, None, None]:
    source_path = local_path.expanduser().absolute()
    if not source_path.exists():
        raise FileNotFoundError(source_path)
    if not zip_requested and encryption_mode is None:
        yield source_path
        return

    with TemporaryDirectory(prefix="stackops-cloud-upload-") as temporary_directory:
        staging_root = Path(temporary_directory)
        if zip_requested:
            upload_path = path_compression.zip_path(
                source_path,
                path=None,
                folder=staging_root,
                name=source_path.name,
                arcname=None,
                inplace=False,
                verbose=True,
                content=False,
                orig=False,
                mode="w",
                included_relative_paths=None,
            )
        else:
            if not source_path.is_file():
                raise IsADirectoryError("Encryption without ZIP compression requires a file source.")
            upload_path = staging_root / source_path.name
            shutil.copy2(source_path, upload_path)

        match encryption_mode:
            case "asymmetric":
                upload_path = encrypt_file_asymmetric(file_path=upload_path, recipient=None)
            case "symmetric":
                upload_path = encrypt_file_symmetric(file_path=upload_path, pwd=_symmetric_password(pwd))
            case None:
                pass
        yield upload_path


@contextmanager
def staged_download(
    *,
    target_path: Path,
    zip_requested: bool,
    encryption_mode: EncryptionMode | None,
) -> Generator[StagedDownload, None, None]:
    resolved_target = target_path.expanduser().absolute()
    if resolved_target.name == "":
        raise ValueError("Cloud copy target must have a final path component.")
    resolved_target.parent.mkdir(parents=True, exist_ok=True)
    prefix = f".{resolved_target.name}.stackops-download-"
    with TemporaryDirectory(prefix=prefix, dir=resolved_target.parent) as temporary_directory:
        staging_root = Path(temporary_directory)
        artifact_root = staging_root / "artifact"
        artifact_root.mkdir()
        yield StagedDownload(
            artifact_path=artifact_path(
                artifact_root / resolved_target.name,
                zip_requested=zip_requested,
                encryption_mode=encryption_mode,
            ),
            staging_root=staging_root,
            target_path=resolved_target,
        )


def _archive_root_name(archive_path: Path) -> str:
    with zipfile.ZipFile(archive_path, "r") as archive:
        root_names: set[str] = set()
        for raw_name in archive.namelist():
            if raw_name == "":
                continue
            member_path = PurePosixPath(raw_name)
            if member_path.is_absolute() or ".." in member_path.parts or len(member_path.parts) == 0:
                raise ValueError(f"ZIP archive contains an invalid member path: {raw_name}")
            root_names.add(member_path.parts[0])
    if len(root_names) != 1:
        raise ValueError(f"Expected one top-level path in ZIP archive, found {len(root_names)}.")
    return next(iter(root_names))


def restore_staged_download(
    *,
    staged: StagedDownload,
    zip_requested: bool,
    encryption_mode: EncryptionMode | None,
    pwd: str | None,
) -> Path:
    if not staged.artifact_path.exists():
        raise FileNotFoundError(f"Downloaded artifact does not exist: {staged.artifact_path}")
    restored_artifact = staged.artifact_path
    match encryption_mode:
        case "asymmetric":
            restored_artifact = decrypt_file_asymmetric(file_path=restored_artifact)
        case "symmetric":
            restored_artifact = decrypt_file_symmetric(file_path=restored_artifact, pwd=_symmetric_password(pwd))
        case None:
            pass

    restored_root = staged.staging_root / "restored"
    restored_root.mkdir()
    restored_path = restored_root / staged.target_path.name
    if not zip_requested:
        restored_artifact.rename(restored_path)
        return restored_path

    archive_root_name = _archive_root_name(restored_artifact)
    extraction_root = staged.staging_root / "extracted"
    path_compression.unzip_path(
        restored_artifact,
        folder=extraction_root,
        path=None,
        name=None,
        verbose=True,
        content=True,
        inplace=False,
        overwrite=False,
        orig=False,
        pwd=None,
        tmp=False,
        pattern=None,
        merge=False,
    )
    extracted_path = extraction_root / archive_root_name
    if not extracted_path.exists() and not extracted_path.is_symlink():
        raise FileNotFoundError(f"ZIP archive did not produce its declared top-level path: {archive_root_name}")
    extracted_path.rename(restored_path)
    return restored_path
