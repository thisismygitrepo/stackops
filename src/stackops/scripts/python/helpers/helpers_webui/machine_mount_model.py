import re
from dataclasses import dataclass
from typing import Literal, TypedDict

from stackops.scripts.python.helpers.helpers_devops.cli_config_mount import MountBackend
from stackops.scripts.python.helpers.helpers_devops.mount_helpers.device_entry import DeviceEntry
from stackops.scripts.python.helpers.helpers_webui.machine_mount_constants import SIZE_PATTERN, SIZE_UNITS

type MountSystem = Literal["Darwin", "Linux", "Windows"]
type DeviceKind = Literal["disk", "part"]
type DeviceState = Literal["ready", "mounted", "blocked"]
# Why the command cannot mount a device. The page has the sentence for each. "no_way" means every way of mounting is ruled out, and `ways` says why.
type BlockCode = Literal["", "apfs_container", "apfs_store", "unreadable", "whole_disk", "bare_disk", "swap", "member", "unlocked", "system_part", "no_way"]
type Encryption = Literal["", "bitlocker", "luks"]
# Why one way of mounting cannot be used for a device.
type WayBlock = Literal["", "other_system", "not_installed", "not_encrypted", "not_bitlocker", "encrypted", "not_elevated", "no_sudo"]
# What a way asks for in the Activity panel when it is given no key file: the administrator password, the device's own password, the account password.
type Ask = Literal["admin", "device", "account"]


@dataclass(frozen=True)
class MountProblem:
    status: int
    message: str


# One of the command's three ways of mounting, as it stands for one device. `places` is false where the system picks the mount point itself.
class MountWay(TypedDict):
    backend: MountBackend
    usable: bool
    why: WayBlock
    asks: list[Ask]
    takes_key: bool
    places: bool
    read_only: bool


# A device as the command lists it, with what the page needs to say about it. `path` is what the command takes as the device. `parent` is the disk a
# part sits on. `inside` counts the volumes an APFS container holds. `ways` is filled for a device that is not mounted and that the system's rules
# do not rule out; `backend` is the way chosen for it, the first usable one in the command's own order.
class MountDevice(TypedDict):
    key: str
    path: str
    kind: DeviceKind
    name: str
    file_system: str
    size: str
    size_bytes: int | None
    about: str
    parent: str
    mounted_at: str
    state: DeviceState
    block: BlockCode
    inside: int
    encryption: Encryption
    ways: list[MountWay]
    backend: MountBackend | None


# `letters` holds the drive letters that are free, on Windows; it is empty elsewhere.
class MountPicture(TypedDict):
    system: MountSystem
    elevated: bool
    letters: list[str]
    devices: list[MountDevice]


# The command prints sizes as text ("460.4 GB", or "465.8G" from lsblk). The page draws and sorts by the number behind it.
def parse_size(text: str | None) -> int | None:
    found = re.fullmatch(SIZE_PATTERN, text.strip()) if text is not None else None
    if found is None:
        return None
    return round(float(found.group(1).replace(",", ".")) * 1024 ** SIZE_UNITS.index(found.group(2)))


# On macOS and Windows the command has one way of mounting, the system's own, whatever is asked for. The other two belong to Linux.
def system_way_only(usable: bool, why: WayBlock) -> list[MountWay]:
    return [
        {"backend": "mount", "usable": usable, "why": why, "asks": [], "takes_key": False, "places": True, "read_only": False},
        {"backend": "dislocker", "usable": False, "why": "other_system", "asks": [], "takes_key": True, "places": True, "read_only": False},
        {"backend": "udisksctl", "usable": False, "why": "other_system", "asks": [], "takes_key": True, "places": False, "read_only": False},
    ]


# `block` is what the system's rules found against the device, or empty. A device they let through is still blocked when no way can be used.
def describe_device(
    entry: DeviceEntry, parent: str, mounted_at: str, block: BlockCode, inside: int, encryption: Encryption, ways: list[MountWay]
) -> MountDevice:
    usable: list[MountBackend] = [way["backend"] for way in ways if way["usable"]]
    state: DeviceState = "mounted" if mounted_at != "" else "ready" if block == "" and len(usable) > 0 else "blocked"
    return {
        "key": entry.key,
        "path": entry.device_path,
        "kind": "disk" if entry.device_type == "disk" else "part",
        "name": entry.label or "",
        "file_system": entry.fs_type or "",
        "size": entry.size or "",
        "size_bytes": parse_size(entry.size),
        "about": entry.extra or "",
        "parent": parent,
        "mounted_at": mounted_at,
        "state": state,
        "block": "" if state != "blocked" else block or "no_way",
        "inside": inside,
        "encryption": encryption,
        "ways": ways if mounted_at == "" and block == "" else [],
        "backend": usable[0] if state == "ready" else None,
    }
