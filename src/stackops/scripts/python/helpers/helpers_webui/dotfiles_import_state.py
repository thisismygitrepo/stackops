import os
import shutil
from pathlib import Path
from typing import TypedDict

from stackops.scripts.python.helpers.helpers_webui.constants import LAUNCH_PATH_VARIABLE
from stackops.scripts.python.helpers.helpers_webui.dotfiles_constants import (
    DOTFILES_ARCHIVE_PATTERN,
    DOTFILES_ARCHIVES_SHOWN,
    DOTFILES_PROTECT_TOOL,
    DOTFILES_TRANSFER_TOOL,
)
from stackops.scripts.python.helpers.helpers_webui.dotfiles_model import ArchiveFile, DotfilesProblem, describe_archive
from stackops.scripts.python.helpers.helpers_webui.other_machines_hosts import SshHost, read_ssh_hosts
from stackops.utils.source_of_truth import DOTFILES_ROOT


# Where this machine stands before anything is brought in: what the dotfiles folder holds now, since an import replaces all of it, the
# archives lying in the home folder, newest first, and what this machine has of the two tools an import can need.
class ImportState(TypedDict):
    folder: str
    exists: bool
    files: int
    size_bytes: int
    archives: list[ArchiveFile]
    can_protect: bool
    can_transfer: bool
    hosts: list[SshHost]


def read_import_state() -> ImportState | DotfilesProblem:
    try:
        sizes = [Path(directory, name).lstat().st_size for directory, _directory_names, names in os.walk(DOTFILES_ROOT) for name in names]
        archives = sorted((describe_archive(path) for path in Path.home().glob(DOTFILES_ARCHIVE_PATTERN) if path.is_file()), key=lambda archive: archive["modified_at"], reverse=True)
    except OSError as error:
        return DotfilesProblem(status=500, message=f"""This machine's folders could not be read: {error}""")
    launch_path = os.environ.get(LAUNCH_PATH_VARIABLE)
    return {
        "folder": str(DOTFILES_ROOT),
        "exists": DOTFILES_ROOT.is_dir(),
        "files": len(sizes),
        "size_bytes": sum(sizes),
        "archives": archives[:DOTFILES_ARCHIVES_SHOWN],
        "can_protect": shutil.which(DOTFILES_PROTECT_TOOL, path=launch_path) is not None,
        "can_transfer": shutil.which(DOTFILES_TRANSFER_TOOL, path=launch_path) is not None,
        "hosts": read_ssh_hosts(),
    }
