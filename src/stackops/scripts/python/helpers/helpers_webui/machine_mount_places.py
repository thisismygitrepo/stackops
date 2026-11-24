import os
import platform
from pathlib import Path
from typing import Literal, TypedDict

from stackops.scripts.python.helpers.helpers_webui.machine_mount_model import MountProblem

# A folder to mount at: not there yet, empty, holding something, already a mount point, a file, or out of the person's reach.
# A key file: a file, nothing, or a folder.
type PlaceVerdict = Literal["new", "empty", "not_empty", "in_use", "is_file", "no_access", "key", "missing", "is_folder"]


class MountPlace(TypedDict):
    path: str
    verdict: PlaceVerdict


# `own_access` is for a system where the command makes the folder and mounts as the person, with no administrator to fall back on.
# A folder that cannot be looked into counts as holding something: the warning that goes with it is the careful one.
def _folder_verdict(path: Path, own_access: bool) -> PlaceVerdict:
    if path.is_dir():
        if os.path.ismount(path):
            return "in_use"
        if own_access and not os.access(path, os.W_OK | os.X_OK):
            return "no_access"
        try:
            return "not_empty" if any(path.iterdir()) else "empty"
        except PermissionError:
            return "no_access" if own_access else "not_empty"
    if path.exists() or path.is_symlink():
        return "is_file"
    holder = next((parent for parent in path.parents if parent.exists()), None)
    if holder is not None and not holder.is_dir():
        return "is_file"
    if holder is None or (own_access and not os.access(holder, os.W_OK | os.X_OK)):
        return "no_access"
    return "new"


# What a typed mount point or key file names, and whether the command can use it. The text is read the way the page's suggestions read it: `~`
# is the home folder and anything relative starts at `base_directory`. The command takes such text as it is, so the page hands it the full path.
def check_mount_place(text: str, base_directory: str, kind: str) -> MountPlace | MountProblem:
    if text.strip() == "":
        return MountProblem(status=400, message="Type a path first.")
    typed = Path(os.path.expanduser(text.strip()))
    path = (typed if typed.is_absolute() else Path(os.path.expanduser(base_directory)) / typed).resolve()
    match kind:
        case "folder":
            return {"path": str(path), "verdict": _folder_verdict(path=path, own_access=platform.system() == "Darwin")}
        case "key":
            return {"path": str(path), "verdict": "key" if path.is_file() else "is_folder" if path.is_dir() else "missing"}
        case _:
            return MountProblem(status=400, message=f"""Unknown kind of place: {kind}""")
