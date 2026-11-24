import json
from dataclasses import dataclass
from typing import cast

from stackops.scripts.python.helpers.helpers_devops.mount_helpers.device_entry import DeviceEntry
from stackops.scripts.python.helpers.helpers_webui.machine_mount_constants import (
    BITLOCKER_MARK,
    LINUX_LUKS_FILE_SYSTEM,
    LINUX_MEMBER_FILE_SYSTEMS,
    LINUX_SWAP_FILE_SYSTEM,
    LINUX_SWAP_MOUNT,
    LINUX_UNLOCKED_KIND,
)
from stackops.scripts.python.helpers.helpers_webui.machine_mount_model import Ask, BlockCode, Encryption, MountDevice, MountWay, WayBlock, describe_device


# What decides which ways of mounting can be used here: whether StackOps runs as root, and which programs are installed.
@dataclass(frozen=True)
class LinuxTools:
    root: bool
    sudo: bool
    dislocker: bool
    udisksctl: bool


# Where the opened content of each unlocked part is mounted, by the part's name, and empty for one that is unlocked with nothing of it mounted
# directly (a volume group inside it, say). The command's own list keeps disks and parts only, so it shows such a part as not mounted.
# `lsblk_json` is what `lsblk -J` prints with the columns in LINUX_UNLOCKED_COLUMNS.
def find_unlocked_places(lsblk_json: str) -> dict[str, str]:
    places: dict[str, str] = {}
    waiting = cast(dict[str, object], json.loads(lsblk_json)).get("blockdevices")
    stack: list[object] = list(cast(list[object], waiting)) if isinstance(waiting, list) else []
    while stack:
        item = stack.pop()
        if not isinstance(item, dict):
            continue
        record = cast(dict[str, object], item)
        part_name, place, children = record.get("pkname"), record.get("mountpoint"), record.get("children")
        if record.get("type") == LINUX_UNLOCKED_KIND and isinstance(part_name, str):
            places[part_name] = place if isinstance(place, str) else ""
        if isinstance(children, list):
            stack.extend(cast(list[object], children))
    return places


# The standard way runs `sudo mount`, and so does dislocker, which is for BitLocker parts only. udisksctl needs no administrator: it unlocks an
# encrypted part and mounts it where the system chooses. It starts by unlocking, so it fails on a part that is not encrypted.
def _linux_ways(encryption: Encryption, tools: LinuxTools) -> list[MountWay]:
    can_elevate = tools.root or tools.sudo
    admin: list[Ask] = [] if tools.root else ["admin"]
    mount_why: WayBlock = "encrypted" if encryption != "" else "" if can_elevate else "no_sudo"
    dislocker_why: WayBlock = "not_bitlocker" if encryption != "bitlocker" else "not_installed" if not tools.dislocker else "" if can_elevate else "no_sudo"
    udisksctl_why: WayBlock = "not_encrypted" if encryption == "" else "" if tools.udisksctl else "not_installed"
    return [
        {"backend": "mount", "usable": mount_why == "", "why": mount_why, "asks": admin, "takes_key": False, "places": True, "read_only": True},
        {"backend": "dislocker", "usable": dislocker_why == "", "why": dislocker_why, "asks": ["device", *admin], "takes_key": True, "places": True, "read_only": True},
        {"backend": "udisksctl", "usable": udisksctl_why == "", "why": udisksctl_why, "asks": ["device", "account"], "takes_key": True, "places": False, "read_only": True},
    ]


# The command mounts parts, never a disk as a whole. Swap, a member of a volume group or an array, and a part with no file system have nothing
# to mount. A part that is already unlocked counts as mounted where its content is, and as in use when that content is not mounted directly.
def describe_linux_devices(entries: list[DeviceEntry], tools: LinuxTools, unlocked: dict[str, str]) -> list[MountDevice]:
    disks = [entry.key for entry in entries if entry.device_type == "disk"]
    parents = {
        entry.key: max((disk for disk in disks if entry.key != disk and entry.key.startswith(disk)), key=len, default="")
        for entry in entries
        if entry.device_type == "part"
    }
    devices: list[MountDevice] = []
    for entry in entries:
        file_system = entry.fs_type or ""
        encryption: Encryption = "bitlocker" if BITLOCKER_MARK in file_system.lower() else "luks" if file_system == LINUX_LUKS_FILE_SYSTEM else ""
        in_swap = entry.mount_point == LINUX_SWAP_MOUNT or file_system == LINUX_SWAP_FILE_SYSTEM
        mounted_at = "" if in_swap else entry.mount_point or unlocked.get(entry.key, "")
        block: BlockCode = ""
        if entry.device_type == "disk":
            block = "whole_disk" if entry.key in parents.values() else "bare_disk"
        elif in_swap:
            block = "swap"
        elif entry.key in unlocked:
            block = "unlocked"
        elif file_system == "":
            block = "unreadable"
        elif file_system in LINUX_MEMBER_FILE_SYSTEMS:
            block = "member"
        devices.append(
            describe_device(
                entry=entry,
                parent=parents.get(entry.key, ""),
                mounted_at=mounted_at,
                block=block,
                inside=0,
                encryption=encryption,
                ways=_linux_ways(encryption=encryption, tools=tools),
            )
        )
    return devices
