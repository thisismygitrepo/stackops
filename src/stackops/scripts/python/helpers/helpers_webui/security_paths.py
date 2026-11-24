import os
from pathlib import Path
from typing import Literal, TypedDict

type PathKind = Literal["file", "folder", "missing", "other"]


# What sits at a path: a file, a folder with the files under it counted, or nothing. `capped` says the count stopped at the limit.
class PathMeasure(TypedDict):
    path: str
    name: str
    kind: PathKind
    size: int
    files: int
    capped: bool
    modified: float | None
    in_home: bool


# Typed text as a place on this machine: `~` expanded, and relative text taken from the working folder, as the path suggestions read it.
def resolve_typed_path(text: str, base_directory: str) -> Path:
    typed = Path(os.path.expanduser(text.strip()))
    return Path(os.path.normpath(typed if typed.is_absolute() else Path(os.path.expanduser(base_directory)) / typed))


def measure_path(path: Path, limit: int) -> PathMeasure:
    measure: PathMeasure = {
        "path": str(path), "name": path.name, "kind": "missing", "size": 0, "files": 0, "capped": False, "modified": None, "in_home": path.is_relative_to(Path.home()),
    }
    try:
        found = path.stat()
    except OSError:
        return measure
    measure["modified"] = found.st_mtime
    if path.is_file():
        measure.update(kind="file", size=found.st_size, files=1)
        return measure
    if not path.is_dir():
        measure["kind"] = "other"
        return measure
    measure["kind"] = "folder"
    for folder, _folders, names in os.walk(path):
        for name in names:
            if measure["files"] >= limit:
                measure["capped"] = True
                return measure
            try:
                measure["size"] += os.lstat(os.path.join(folder, name)).st_size
            except OSError:
                continue
            measure["files"] += 1
    return measure
