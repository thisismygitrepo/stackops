import os
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

from stackops.utils.source_of_truth import DOTFILES_ZIP_PATH


@dataclass(frozen=True, slots=True)
class DotfilesProblem:
    status: int
    message: str


class ArchiveFile(TypedDict):
    path: str
    exists: bool
    size_bytes: int
    modified_at: float


# Where the export command leaves its archive when no other place is given: the zip's path with the ending encryption adds.
DEFAULT_ARCHIVE_PATH = DOTFILES_ZIP_PATH.with_name(f"""{DOTFILES_ZIP_PATH.name}.gpg""")


def describe_archive(path: Path) -> ArchiveFile:
    if not path.is_file():
        return {"path": str(path), "exists": False, "size_bytes": 0, "modified_at": 0.0}
    facts = path.stat()
    return {"path": str(path), "exists": True, "size_bytes": facts.st_size, "modified_at": facts.st_mtime}


# A path as it was typed into the page, read the way a run in `base_directory` would read it. Links are kept as they are.
def typed_path(text: str, base_directory: str) -> Path:
    typed = Path(os.path.expanduser(text.strip()))
    return typed if typed.is_absolute() else Path(os.path.expanduser(base_directory)).joinpath(typed).absolute()
