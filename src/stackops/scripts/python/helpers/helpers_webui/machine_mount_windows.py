import os
import sys

from stackops.scripts.python.helpers.helpers_devops.mount_helpers.device_entry import DeviceEntry
from stackops.scripts.python.helpers.helpers_webui.machine_mount_constants import WINDOWS_DRIVE_LETTERS, WINDOWS_SYSTEM_PART_TYPES, WINDOWS_UNREADABLE_PART_TYPE
from stackops.scripts.python.helpers.helpers_webui.machine_mount_model import BlockCode, MountDevice, describe_device, system_way_only


# The letters no drive has yet. Everything that has one counts: parts, network drives, card readers.
def read_free_letters() -> list[str]:
    if sys.platform != "win32":
        return []
    taken = {drive[:1].upper() for drive in os.listdrives()}
    return [letter for letter in WINDOWS_DRIVE_LETTERS if letter not in taken]


# Mounting on Windows is giving a part a drive letter, which only an administrator may do: the command does not ask for those rights, so it
# works when StackOps itself was started with them. A part with a letter counts as mounted. The parts Windows keeps for itself are left alone.
def describe_windows_devices(entries: list[DeviceEntry], elevated: bool) -> list[MountDevice]:
    devices: list[MountDevice] = []
    for entry in entries:
        part_type = entry.extra or ""
        block: BlockCode = "system_part" if part_type in WINDOWS_SYSTEM_PART_TYPES else "unreadable" if part_type == WINDOWS_UNREADABLE_PART_TYPE else ""
        devices.append(
            describe_device(
                entry=entry,
                parent=f"""Disk {entry.disk_number}""" if entry.disk_number is not None else "",
                mounted_at=f"""{entry.drive_letter}:\\""" if entry.drive_letter is not None else "",
                block=block,
                inside=0,
                encryption="",
                ways=system_way_only(usable=elevated, why="" if elevated else "not_elevated"),
            )
        )
    return devices
