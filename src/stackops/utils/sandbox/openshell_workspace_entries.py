import hashlib
import os
import shutil
import stat
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal


@dataclass(frozen=True, slots=True)
class WorkspaceEntry:
    kind: Literal["file", "directory", "symlink", "other"]
    mode: int
    value: str | None


def read_workspace_entry(path: Path) -> WorkspaceEntry | None:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return None
    mode = stat.S_IMODE(metadata.st_mode)
    if stat.S_ISREG(metadata.st_mode):
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        return WorkspaceEntry(kind="file", mode=mode, value=digest)
    if stat.S_ISDIR(metadata.st_mode):
        return WorkspaceEntry(kind="directory", mode=mode, value=None)
    if stat.S_ISLNK(metadata.st_mode):
        return WorkspaceEntry(kind="symlink", mode=0, value=os.readlink(path))
    return WorkspaceEntry(kind="other", mode=mode, value=str(stat.S_IFMT(metadata.st_mode)))


def read_workspace_entries(*, directory: Path, selected: set[Path] | None, include_git: bool) -> dict[Path, WorkspaceEntry]:
    root = read_workspace_entry(directory)
    if root is None or root.kind != "directory":
        raise ValueError(f"""Workspace must be a directory, not a symlink: {directory}""")
    entries: dict[Path, WorkspaceEntry] = {}
    pending = [directory]
    while pending:
        parent = pending.pop()
        for path in sorted(parent.iterdir()):
            relative = path.relative_to(directory)
            if (path.name == ".git" and not include_git) or (selected is not None and relative not in selected):
                continue
            entry = read_workspace_entry(path)
            if entry is None:
                continue
            entries[relative] = entry
            if entry.kind == "directory" and path.name != ".git":
                pending.append(path)
    return entries


def has_directory_ancestors(*, directory: Path, relative: Path) -> bool:
    for ancestor in reversed(relative.parents):
        entry = read_workspace_entry(directory / ancestor)
        if entry is not None and entry.kind != "directory":
            return False
    return True


def copy_workspace_entry(*, source: Path, destination: Path) -> None:
    with TemporaryDirectory(prefix=".stackops-openshell-", dir=destination.parent) as staging:
        staged = Path(staging) / "entry"
        shutil.copy2(source, staged, follow_symlinks=False)
        os.replace(staged, destination)
