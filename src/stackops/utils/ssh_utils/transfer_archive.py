from collections.abc import Generator
from contextlib import contextmanager
from pathlib import PurePath
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from paramiko import SFTPClient


@contextmanager
def remote_transfer_archive(sftp: "SFTPClient", parent: PurePath) -> Generator[str]:
    directory = parent / f".stackops-{uuid4().hex}"
    path = str(directory / "payload.zip")
    sftp.mkdir(str(directory), mode=0o700)
    try:
        yield path
    finally:
        try:
            sftp.remove(path)
        except FileNotFoundError:
            pass
        finally:
            sftp.rmdir(str(directory))


def create_transfer_archive(source_path: str, archive_path: str) -> None:
    from pathlib import Path
    import shutil

    source = Path(source_path)
    archive_base = archive_path.removesuffix(".zip")
    if source.is_dir():
        shutil.make_archive(archive_base, "zip", source)
    else:
        shutil.make_archive(archive_base, "zip", source.parent, source.name)


def extract_uploaded_archive(archive_path: str, target_path: str, overwrite: bool, root_mode: int | None) -> None:
    from pathlib import Path
    import shutil
    import stat
    import zipfile

    target = Path(target_path)
    if overwrite and target.exists():
        shutil.rmtree(target)
    target.mkdir()
    with zipfile.ZipFile(archive_path, "r") as archive:
        if root_mode is None:
            archive.extractall(target)
        else:
            target.chmod(0o700)
            directory_modes: list[tuple[Path, int]] = []
            for member in archive.infolist():
                extracted_path = Path(archive.extract(member, target))
                mode = stat.S_IMODE(member.external_attr >> 16)
                if member.is_dir():
                    directory_modes.append((extracted_path, mode))
                else:
                    extracted_path.chmod(mode)
            for directory, mode in sorted(directory_modes, key=lambda item: len(item[0].parts), reverse=True):
                directory.chmod(mode)
            target.chmod(root_mode)
