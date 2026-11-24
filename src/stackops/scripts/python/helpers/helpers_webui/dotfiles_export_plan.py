import os
import shutil
from pathlib import Path
from typing import Literal, TypedDict

from stackops.scripts.python.helpers.helpers_devops.network_service import require_free_port
from stackops.scripts.python.helpers.helpers_webui.constants import LAUNCH_PATH_VARIABLE
from stackops.scripts.python.helpers.helpers_webui.dotfiles_constants import (
    DOTFILES_LEFT_OUT_EXAMPLES,
    DOTFILES_PROTECT_TOOL,
    DOTFILES_SHARE_HOST,
    DOTFILES_SHARE_PORT,
    DOTFILES_SHARE_TOOL,
    DOTFILES_TRANSFER_TOOL,
)
from stackops.scripts.python.helpers.helpers_webui.dotfiles_model import DEFAULT_ARCHIVE_PATH, ArchiveFile, DotfilesProblem, describe_archive
from stackops.scripts.python.helpers.helpers_webui.other_machines_hosts import SshHost, read_ssh_hosts
from stackops.utils.network.address import select_lan_ipv4
from stackops.utils.source_of_truth import DOTFILES_ROOT, DOTFILES_USER_MAPPER_PATH

type LeftOutReason = Literal["broken_link", "special_file", "linked_folder"]


# One folder at the top of the dotfiles folder, or the files that lie loose there (`name` is then empty).
class ExportPart(TypedDict):
    name: str
    files: int
    size_bytes: int


class LeftOut(TypedDict):
    reason: LeftOutReason
    count: int
    examples: list[str]


# What sharing over the local network needs: its tool, an address other machines can reach, and the port the command always uses.
class NetworkShare(TypedDict):
    tool_installed: bool
    address: str
    port: int
    port_free: bool


class ExportPlan(TypedDict):
    folder: str
    exists: bool
    files: int
    size_bytes: int
    parts: list[ExportPart]
    left_out: list[LeftOut]
    list_inside: bool
    archive: ArchiveFile
    can_protect: bool
    share: NetworkShare
    can_transfer: bool
    hosts: list[SshHost]


# What an export made now would hold. The command zips the whole folder with `shutil.make_archive`, which walks it without following links to
# folders and adds a file only when it is a regular file or a link to one. The walk here is the same one, so the numbers are the archive's.
def read_export_plan() -> ExportPlan | DotfilesProblem:
    parts: dict[str, ExportPart] = {}
    left_out: dict[LeftOutReason, list[str]] = {"broken_link": [], "special_file": [], "linked_folder": []}
    exists = DOTFILES_ROOT.is_dir()
    try:
        for directory, directory_names, file_names in os.walk(DOTFILES_ROOT):
            inside = Path(directory).relative_to(DOTFILES_ROOT)
            left_out["linked_folder"].extend(inside.joinpath(name).as_posix() for name in directory_names if Path(directory, name).is_symlink())
            for name in file_names:
                path = Path(directory, name)
                if not path.is_file():
                    left_out["broken_link" if path.is_symlink() else "special_file"].append(inside.joinpath(name).as_posix())
                    continue
                top = inside.parts[0] if len(inside.parts) > 0 else ""
                part = parts.setdefault(top, {"name": top, "files": 0, "size_bytes": 0})
                part["files"] += 1
                part["size_bytes"] += path.stat().st_size
    except OSError as error:
        return DotfilesProblem(status=500, message=f"""The dotfiles folder could not be read: {error}""")
    launch_path = os.environ.get(LAUNCH_PATH_VARIABLE)
    try:
        require_free_port(DOTFILES_SHARE_HOST, DOTFILES_SHARE_PORT)
        port_free = True
    except RuntimeError:
        port_free = False
    return {
        "folder": str(DOTFILES_ROOT),
        "exists": exists,
        "files": sum(part["files"] for part in parts.values()),
        "size_bytes": sum(part["size_bytes"] for part in parts.values()),
        "parts": sorted(parts.values(), key=lambda part: part["size_bytes"], reverse=True),
        "left_out": [
            {"reason": reason, "count": len(paths), "examples": sorted(paths)[:DOTFILES_LEFT_OUT_EXAMPLES]} for reason, paths in left_out.items() if len(paths) > 0
        ],
        "list_inside": DOTFILES_USER_MAPPER_PATH.is_file(),
        "archive": describe_archive(DEFAULT_ARCHIVE_PATH),
        "can_protect": shutil.which(DOTFILES_PROTECT_TOOL, path=launch_path) is not None,
        "share": {
            "tool_installed": shutil.which(DOTFILES_SHARE_TOOL, path=launch_path) is not None,
            "address": select_lan_ipv4(prefer_vpn=False) or "",
            "port": DOTFILES_SHARE_PORT,
            "port_free": port_free,
        },
        "can_transfer": shutil.which(DOTFILES_TRANSFER_TOOL, path=launch_path) is not None,
        "hosts": read_ssh_hosts(),
    }
