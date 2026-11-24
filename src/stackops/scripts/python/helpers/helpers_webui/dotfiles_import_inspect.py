import os
import shutil
import tempfile
import zipfile
import zlib
from pathlib import Path
from typing import Literal, TypedDict
from urllib.parse import urlparse

from stackops.scripts.python.helpers.helpers_webui.dotfiles_constants import DOTFILES_HASH_CHUNK_BYTES, DOTFILES_LISTING_ROWS
from stackops.scripts.python.helpers.helpers_webui.dotfiles_model import DotfilesProblem, typed_path
from stackops.utils.files.download import download
from stackops.utils.io import GpgCommandError, decrypt_file_symmetric
from stackops.utils.source_of_truth import DOTFILES_ROOT, DOTFILES_USER_MAPPER_PATH

# What becomes of a file when the archive is brought in. The import command replaces the whole folder, so a file that is only here is removed.
type FileFate = Literal["removed", "replaced", "new", "same"]
FATES: tuple[FileFate, ...] = ("removed", "replaced", "new", "same")


class ListedFile(TypedDict):
    path: str
    size_bytes: int
    fate: FileFate


# `rows` holds what changes first and is cut at a limit; `rows_cut` is how many more there are. `has_list` says the archive carries the list of
# managed files, which is what "Apply to this machine" works from afterwards.
class ArchiveListing(TypedDict):
    folder_exists: bool
    counts: dict[FileFate, int]
    sizes: dict[FileFate, int]
    rows: list[ListedFile]
    rows_cut: int
    has_list: bool


def _open_archive(source: str, password: str, base_directory: str, scratch: str) -> list[zipfile.ZipInfo] | DotfilesProblem:
    if urlparse(source).scheme in {"http", "https"}:
        encrypted = download(url=source, decompress=False, output=None, output_dir=scratch)
        if encrypted is None:
            return DotfilesProblem(status=502, message="Nothing could be fetched from that address. Check that the other machine is still sharing and that both are on the same network.")
    else:
        local = typed_path(text=source, base_directory=base_directory)
        if not local.is_file():
            return DotfilesProblem(status=404, message=f"""There is no file at {local}.""")
        encrypted = Path(shutil.copyfile(local, Path(scratch, local.name)))
    try:
        opened = decrypt_file_symmetric(file_path=encrypted, pwd=password)
    except GpgCommandError as error:
        if "no valid OpenPGP data" in error.stderr:
            return DotfilesProblem(status=422, message="That file is not a protected archive.")
        return DotfilesProblem(status=403, message="That password does not open this archive.")
    except RuntimeError:
        return DotfilesProblem(status=501, message="GnuPG is not installed on this machine, so the archive cannot be opened.")
    try:
        with zipfile.ZipFile(opened) as archive:
            return [member for member in archive.infolist() if not member.is_dir()]
    except zipfile.BadZipFile:
        return DotfilesProblem(status=422, message="The password opened the file, but what is inside is not a dotfiles archive.")


def _matches(path: Path, member: zipfile.ZipInfo) -> bool:
    if path.stat().st_size != member.file_size:
        return False
    checksum = 0
    with path.open("rb") as stream:
        while chunk := stream.read(DOTFILES_HASH_CHUNK_BYTES):
            checksum = zlib.crc32(chunk, checksum)
    return checksum == member.CRC


# Opens the archive in a private scratch folder, which is removed again, and compares its listing with the dotfiles folder as it is now.
# Nothing is unpacked and nothing under the dotfiles folder is touched. The password comes in the request's body and is kept nowhere.
def inspect_archive(body: object) -> ArchiveListing | DotfilesProblem:
    match body:
        case {"source": str() as source, "password": str() as password, "base": str() as base_directory} if source.strip() != "" and password != "":
            pass
        case _:
            return DotfilesProblem(status=400, message="Name the archive and give its password.")
    with tempfile.TemporaryDirectory(prefix="stackops-dotfiles-look-") as scratch:
        members = _open_archive(source=source.strip(), password=password, base_directory=base_directory, scratch=scratch)
    match members:
        case DotfilesProblem():
            return members
        case _:
            archived = {member.filename: member for member in members}
    if any(Path(name).is_absolute() or ".." in Path(name).parts for name in archived):
        return DotfilesProblem(status=422, message="This archive names a place outside the dotfiles folder. The import refuses an archive like that.")
    rows: list[ListedFile] = []
    try:
        for name, member in archived.items():
            here = DOTFILES_ROOT.joinpath(name)
            fate: FileFate = "new" if not here.is_file() else "same" if _matches(path=here, member=member) else "replaced"
            rows.append({"path": name, "size_bytes": member.file_size, "fate": fate})
        for directory, _directory_names, file_names in os.walk(DOTFILES_ROOT):
            for file_name in file_names:
                path = Path(directory, file_name)
                inside = path.relative_to(DOTFILES_ROOT).as_posix()
                if inside not in archived:
                    rows.append({"path": inside, "size_bytes": path.lstat().st_size, "fate": "removed"})
    except OSError as error:
        return DotfilesProblem(status=500, message=f"""The dotfiles folder could not be read: {error}""")
    rows.sort(key=lambda row: (FATES.index(row["fate"]), row["path"]))
    return {
        "folder_exists": DOTFILES_ROOT.is_dir(),
        "counts": {fate: sum(row["fate"] == fate for row in rows) for fate in FATES},
        "sizes": {fate: sum(row["size_bytes"] for row in rows if row["fate"] == fate) for fate in FATES},
        "rows": rows[:DOTFILES_LISTING_ROWS],
        "rows_cut": max(len(rows) - DOTFILES_LISTING_ROWS, 0),
        "has_list": DOTFILES_USER_MAPPER_PATH.relative_to(DOTFILES_ROOT).as_posix() in archived,
    }
