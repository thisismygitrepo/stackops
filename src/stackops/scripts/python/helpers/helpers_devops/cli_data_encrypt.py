import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Annotated, Literal, NoReturn, TypeAlias

import typer

from stackops.scripts.python.helpers.helpers_devops.cli_data_encrypt_output import publish_output, validate_output
from stackops.utils.cloud.encryption import ENCRYPTION_MODES_DISPLAY, EncryptionMode, EncryptionModeChoice, parse_encryption_mode
from stackops.utils.files.compression import DECOMPRESS_SUPPORTED_FORMATS
from stackops.utils.path_core import tmp

DATA_ENCRYPT_HELP = "🔐 <x> Encrypt a file or folder with symmetric or asymmetric GPG."
DATA_DECRYPT_HELP = "🔓 <y> Decrypt a GPG file; folder archives are extracted."

FolderArchiveFormat: TypeAlias = Literal["zip", "tar.gz", "tar.bz2", "tar.xz"]
FOLDER_ARCHIVE_SUFFIXES: dict[FolderArchiveFormat, str] = {
    "zip": ".zip",
    "tar.gz": ".tar.gz",
    "tar.bz2": ".tar.bz2",
    "tar.xz": ".tar.xz",
}
ARCHIVE_SUFFIXES_LONGEST_FIRST: tuple[str, ...] = tuple(sorted(DECOMPRESS_SUPPORTED_FORMATS, key=len, reverse=True))


def _fail(message: str) -> NoReturn:
    typer.echo(typer.style("Error: ", fg=typer.colors.RED) + message)
    raise typer.Exit(code=1)


def _symmetric_password(pwd: str | None, *, prompt: str) -> str:
    if pwd is not None:
        return pwd
    import getpass

    return getpass.getpass(prompt=prompt)


def _resolve_encryption(encryption: EncryptionModeChoice, *, pwd: str | None, recipient: str | None) -> EncryptionMode:
    mode = parse_encryption_mode(encryption, label="encryption")
    if mode == "symmetric" and recipient is not None:
        _fail(f"--recipient requires asymmetric encryption ({ENCRYPTION_MODES_DISPLAY}).")
    if mode == "asymmetric" and pwd is not None:
        _fail(f"--password requires symmetric encryption ({ENCRYPTION_MODES_DISPLAY}).")
    return mode


def _match_archive_suffix(name: str) -> str | None:
    for suffix in ARCHIVE_SUFFIXES_LONGEST_FIRST:
        if name.endswith(suffix) and len(name) > len(suffix):
            return suffix
    return None


def encrypt(
    path: Annotated[Path, typer.Argument(help="📄 File or folder to encrypt. Folders are archived before encryption.")],
    encryption: Annotated[
        EncryptionModeChoice,
        typer.Option("--encryption", "-e", help=f"🔐 Encryption mode: {ENCRYPTION_MODES_DISPLAY}. Symmetric uses a password; asymmetric uses GPG keys."),
    ] = "symmetric",
    pwd: Annotated[str | None, typer.Option("--password", "-p", help="🔑 Symmetric GPG password. Prompts with a hidden prompt when omitted.")] = None,
    recipient: Annotated[
        str | None,
        typer.Option("--recipient", "-r", help="🪪 Asymmetric GPG recipient key (id, email, or fingerprint). Defaults to your own key."),
    ] = None,
    compression: Annotated[
        FolderArchiveFormat,
        typer.Option("--compression", "-c", help="🗜 Archive format for folders: zip, tar.gz, tar.bz2, or tar.xz. Ignored for files."),
    ] = "zip",
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="📦 Encrypted output path. Defaults to <path>.parent/<name>[.<compression>].gpg."),
    ] = None,
    overwrite: Annotated[bool, typer.Option("--overwrite", "-f", help="Replace the existing output file or entire folder.")] = False,
) -> None:
    mode = _resolve_encryption(encryption, pwd=pwd, recipient=recipient)
    source = path.expanduser().absolute()
    if not source.exists():
        _fail(f"Path does not exist: {source}")
    output_path = output.expanduser().absolute() if output is not None else _default_encrypted_output(source, compression=compression)
    try:
        validate_output(source=source, output_path=output_path, overwrite=overwrite)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        _encrypt_to_output(
            source=source, mode=mode, pwd=pwd, recipient=recipient, compression=compression, output_path=output_path, overwrite=overwrite
        )
    except (OSError, ValueError, RuntimeError) as exc:
        _fail(str(exc))
    typer.echo(typer.style("✅ Success: ", fg=typer.colors.GREEN) + f"Encrypted {source} ==> {output_path}")


def decrypt(
    path: Annotated[Path, typer.Argument(help="🔐 Encrypted .gpg file to decrypt.")],
    encryption: Annotated[
        EncryptionModeChoice,
        typer.Option("--encryption", "-e", help=f"🔓 Encryption mode used to create the file: {ENCRYPTION_MODES_DISPLAY}."),
    ] = "symmetric",
    pwd: Annotated[str | None, typer.Option("--password", "-p", help="🔑 Symmetric GPG password. Prompts with a hidden prompt when omitted.")] = None,
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="📦 Decrypted output path. Defaults next to the encrypted file with .gpg and archive suffixes stripped."),
    ] = None,
    overwrite: Annotated[bool, typer.Option("--overwrite", "-f", help="Replace the existing output file or entire folder.")] = False,
) -> None:
    mode = parse_encryption_mode(encryption, label="encryption")
    source = path.expanduser().absolute()
    if not source.is_file():
        _fail(f"Encrypted file does not exist: {source}")
    if source.suffix != ".gpg":
        _fail(f"Expected a .gpg encrypted file: {source}")
    inner_name = source.name.removesuffix(".gpg")
    archive_suffix = _match_archive_suffix(inner_name)
    output_path = output.expanduser().absolute() if output is not None else source.parent / _stripped_artifact_name(inner_name, archive_suffix=archive_suffix)
    try:
        validate_output(source=source, output_path=output_path, overwrite=overwrite)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        _decrypt_to_output(source=source, mode=mode, pwd=pwd, archive_suffix=archive_suffix, output_path=output_path, overwrite=overwrite)
    except (OSError, ValueError, RuntimeError) as exc:
        _fail(str(exc))
    typer.echo(typer.style("✅ Success: ", fg=typer.colors.GREEN) + f"Decrypted {source} ==> {output_path}")


def _default_encrypted_output(source: Path, *, compression: FolderArchiveFormat) -> Path:
    if source.is_dir():
        return source.parent / f"{source.name}{FOLDER_ARCHIVE_SUFFIXES[compression]}.gpg"
    return source.parent / f"{source.name}.gpg"


def _stripped_artifact_name(inner_name: str, *, archive_suffix: str | None) -> str:
    stripped_name = inner_name[: -len(archive_suffix)] if archive_suffix is not None else inner_name
    if stripped_name == "":
        _fail(f"Encrypted file name has no name left after stripping suffixes: {inner_name}")
    return stripped_name


def _encrypt_to_output(
    *,
    source: Path,
    mode: EncryptionMode,
    pwd: str | None,
    recipient: str | None,
    compression: FolderArchiveFormat,
    output_path: Path,
    overwrite: bool,
) -> None:
    from stackops.utils.io import encrypt_file_asymmetric, encrypt_file_symmetric

    with TemporaryDirectory(prefix=".stackops-encrypt-", dir=tmp(folder="stackops/data", file=None, root="~/tmp_results")) as temporary_directory:
        staging_root = Path(temporary_directory)
        staged_input = _stage_input(source, compression=compression, staging_root=staging_root)
        match mode:
            case "symmetric":
                encrypt_file_symmetric(file_path=staged_input, pwd=_symmetric_password(pwd, prompt="🔑 Enter symmetric GPG encryption password: "))
            case "asymmetric":
                encrypt_file_asymmetric(file_path=staged_input, recipient=recipient)
        publish_output(source=source, staged_path=staging_root / f"{staged_input.name}.gpg", output_path=output_path, overwrite=overwrite)


def _stage_input(source: Path, *, compression: FolderArchiveFormat, staging_root: Path) -> Path:
    import stackops.utils.files.compression as path_compression

    if not source.is_dir():
        staged_input = staging_root / source.name
        shutil.copy2(source, staged_input)
        return staged_input
    match compression:
        case "zip":
            return path_compression.zip_path(
                source,
                path=staging_root / f"{source.name}.zip",
                folder=None,
                name=None,
                arcname=None,
                inplace=False,
                verbose=False,
                content=False,
                orig=False,
                mode="w",
                included_relative_paths=None,
            )
        case "tar.gz" | "tar.bz2" | "tar.xz":
            return path_compression.tar_path(
                source,
                path=staging_root / f"{source.name}{FOLDER_ARCHIVE_SUFFIXES[compression]}",
                folder=None,
                name=None,
                arcname=None,
                tar_format=compression,
                inplace=False,
                orig=False,
                verbose=False,
            )


def _decrypt_to_output(
    *, source: Path, mode: EncryptionMode, pwd: str | None, archive_suffix: str | None, output_path: Path, overwrite: bool
) -> None:
    from stackops.utils.io import decrypt_file_asymmetric, decrypt_file_symmetric

    with TemporaryDirectory(prefix=".stackops-decrypt-", dir=tmp(folder="stackops/data", file=None, root="~/tmp_results")) as temporary_directory:
        staging_root = Path(temporary_directory)
        staged_encrypted = staging_root / source.name
        shutil.copy2(source, staged_encrypted)
        match mode:
            case "symmetric":
                decrypted_artifact = decrypt_file_symmetric(
                    file_path=staged_encrypted, pwd=_symmetric_password(pwd, prompt="🔑 Enter symmetric GPG decryption password: ")
                )
            case "asymmetric":
                decrypted_artifact = decrypt_file_asymmetric(file_path=staged_encrypted)
        staged_output = decrypted_artifact if archive_suffix is None else _restore_archive(artifact=decrypted_artifact, staging_root=staging_root)
        publish_output(source=source, staged_path=staged_output, output_path=output_path, overwrite=overwrite)


def _restore_archive(*, artifact: Path, staging_root: Path) -> Path:
    import stackops.utils.files.compression as path_compression

    extraction_root = staging_root / "extracted"
    extraction_root.mkdir()
    if artifact.name.endswith(".zip"):
        path_compression.unzip_path(
            artifact,
            folder=extraction_root,
            path=None,
            name=None,
            verbose=False,
            content=True,
            inplace=False,
            overwrite=False,
            orig=False,
            pwd=None,
            tmp=False,
            pattern=None,
            merge=False,
        )
        payload = extraction_root
    else:
        payload = path_compression.decompress_path(artifact, folder=extraction_root, name=None, path=None, inplace=False, orig=False, verbose=False)
    if payload.is_file():
        return payload
    entries = sorted(payload.iterdir(), key=lambda entry: entry.name)
    if len(entries) == 0:
        raise ValueError("Archive is empty; nothing to restore.")
    return entries[0] if len(entries) == 1 else payload
