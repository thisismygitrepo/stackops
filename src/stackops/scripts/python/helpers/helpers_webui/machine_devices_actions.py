import re
from pathlib import Path

from stackops.scripts.python.helpers.helpers_devops.mount_helpers.commands import ensure_ok, run_command
from stackops.scripts.python.helpers.helpers_devops.mount_helpers.device_entry import DeviceEntry
from stackops.scripts.python.helpers.helpers_devops.mount_helpers.macos import mount_macos
from stackops.scripts.python.helpers.helpers_webui.machine_devices_model import StorageProblem, StorageVolume, VolumeAction
from stackops.scripts.python.helpers.helpers_webui.machine_devices_read import read_storage

GONE = "It is no longer there. It may have been unplugged or ejected already."
# How macOS names the program that kept a volume from being unmounted: its process number, then the path of the program.
HOLDER = re.compile(r"dissented by PID (\d+) \(([^)]*)\)")


def _failure(error: RuntimeError, name: str) -> StorageProblem:
    said = " ".join(str(error).split())
    holder = HOLDER.search(said)
    if holder is None:
        return StorageProblem(reason="failed", message=said)
    program = Path(holder.group(2)).name
    return StorageProblem(reason="failed", message=f"""{name} is in use by {program} (process {holder.group(1)}), so macOS left it mounted. Close it there, then try again.""")


# What is asked for is looked up in a fresh read and only done when that read offers it. So a request can name nothing but a device this
# machine has now, and the system's own volumes stay out of reach whatever the page sends.
def _offered(identifier: str, action: VolumeAction) -> StorageVolume | StorageProblem:
    picture = read_storage()
    match picture:
        case StorageProblem():
            return picture
        case _:
            volume = next((candidate for disk in picture["disks"] for candidate in disk["volumes"] if candidate["id"] == identifier), None)
    if volume is None:
        return StorageProblem(reason="unknown_device", message=GONE)
    if action not in volume["actions"]:
        return StorageProblem(reason="refused", message=f"""{volume["name"] or identifier} cannot be {action}ed from here.""")
    return volume


# Mounted where macOS puts a volume by default, through the mount command's own helper. That command cannot name a volume inside a pool,
# which is what most Mac disks hold, so the page does not hand those over to it.
def mount_volume(identifier: str) -> StorageProblem | None:
    volume = _offered(identifier=identifier, action="mount")
    match volume:
        case StorageProblem():
            return volume
        case _:
            entry = DeviceEntry(
                platform_name="Darwin", key=volume["id"], device_path=volume["device"], device_type="part", label=volume["name"] or None, mount_point=None,
                fs_type=volume["file_system"] or None, size=None, extra=None, disk_number=None, partition_number=None, drive_letter=None,
            )
    try:
        mount_macos(entry, "-")
    except RuntimeError as error:
        return _failure(error=error, name=volume["name"] or identifier)
    return None


# Never forced: a volume some program still has files open on stays mounted, and the answer says so.
def unmount_volume(identifier: str) -> StorageProblem | None:
    volume = _offered(identifier=identifier, action="unmount")
    match volume:
        case StorageProblem():
            return volume
        case _:
            name = volume["name"] or identifier
    try:
        ensure_ok(run_command(["diskutil", "unmount", identifier]), "Unmounting")
    except RuntimeError as error:
        return _failure(error=error, name=name)
    return None


def eject_disk(identifier: str) -> StorageProblem | None:
    picture = read_storage()
    match picture:
        case StorageProblem():
            return picture
        case _:
            disk = next((candidate for candidate in picture["disks"] if candidate["id"] == identifier), None)
    if disk is None:
        return StorageProblem(reason="unknown_device", message=GONE)
    if not disk["can_eject"]:
        return StorageProblem(reason="refused", message=f"""{disk["name"] or identifier} cannot be ejected from here.""")
    try:
        ensure_ok(run_command(["diskutil", "eject", identifier]), "Ejecting")
    except RuntimeError as error:
        return _failure(error=error, name=disk["name"] or identifier)
    return None
