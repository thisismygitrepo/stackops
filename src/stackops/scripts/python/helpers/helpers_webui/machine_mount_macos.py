import plistlib
import re
from dataclasses import dataclass
from typing import cast

from stackops.scripts.python.helpers.helpers_devops.mount_helpers.commands import ensure_ok, run_command
from stackops.scripts.python.helpers.helpers_devops.mount_helpers.device_entry import DeviceEntry
from stackops.scripts.python.helpers.helpers_webui.machine_mount_constants import MACOS_APFS_STORE_PREFIX, MACOS_SYSTEM_CONTENTS, MACOS_WHOLE_DISK_PATTERN
from stackops.scripts.python.helpers.helpers_webui.machine_mount_model import BlockCode, MountDevice, describe_device, system_way_only


# What `diskutil list` knows beyond the command's own list: what each disk and part holds, and how many volumes each APFS container has.
@dataclass(frozen=True)
class MacLayout:
    contents: dict[str, str]
    volumes: dict[str, int]


def _records(value: object) -> list[dict[str, object]]:
    return [cast(dict[str, object], item) for item in cast(list[object], value) if isinstance(item, dict)] if isinstance(value, list) else []


def read_macos_layout() -> MacLayout:
    text = ensure_ok(run_command(["diskutil", "list", "-plist"]), "diskutil list")
    data = cast(dict[str, object], plistlib.loads(text.encode("utf-8")))
    contents: dict[str, str] = {}
    volumes: dict[str, int] = {}
    for disk in _records(data.get("AllDisksAndPartitions")):
        for holder in [disk, *_records(disk.get("Partitions"))]:
            name, content = holder.get("DeviceIdentifier"), holder.get("Content")
            if isinstance(name, str) and isinstance(content, str):
                contents[name] = content
        disk_name = disk.get("DeviceIdentifier")
        if isinstance(disk_name, str) and "APFSVolumes" in disk:
            volumes[disk_name] = len(_records(disk.get("APFSVolumes")))
    return MacLayout(contents=contents, volumes=volumes)


# The command lists the parts of a disk, and a disk as a whole only when it has none. It does not list the volumes inside an APFS container, so
# a container shows up as a disk with no file system, and so does the part of a disk that stores one. Neither can be mounted, and a startup
# partition is left to the system. Everything else with a file system macOS can read is mounted by macOS itself, at no one's password.
def describe_macos_devices(entries: list[DeviceEntry], layout: MacLayout) -> list[MountDevice]:
    devices: list[MountDevice] = []
    for entry in entries:
        content = layout.contents.get(entry.key, "")
        block: BlockCode = ""
        if entry.key in layout.volumes:
            block = "apfs_container"
        elif content in MACOS_SYSTEM_CONTENTS:
            block = "system_part"
        elif entry.fs_type is None:
            block = "apfs_store" if content.startswith(MACOS_APFS_STORE_PREFIX) else "unreadable"
        whole = re.match(MACOS_WHOLE_DISK_PATTERN, entry.key)
        devices.append(
            describe_device(
                entry=entry,
                parent=whole.group() if whole is not None and entry.device_type == "part" else "",
                mounted_at=entry.mount_point or "",
                block=block,
                inside=layout.volumes.get(entry.key, 0),
                encryption="",
                ways=system_way_only(usable=True, why=""),
            )
        )
    return devices
