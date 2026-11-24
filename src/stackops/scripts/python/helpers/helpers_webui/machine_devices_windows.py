from stackops.scripts.python.helpers.helpers_devops.mount_helpers.devices import list_devices
from stackops.scripts.python.helpers.helpers_webui.machine_devices_model import HELPER_ROLES, StorageDisk, StorageRegion, StorageVolume, VolumeRole
from stackops.scripts.python.helpers.helpers_webui.machine_devices_mounts import Mounted
from stackops.scripts.python.helpers.helpers_webui.machine_devices_records import plain_volume

SIZE_UNITS = ("B", "KB", "MB", "GB", "TB", "PB")
PARTITION_ROLES: dict[str, VolumeRole] = {"System": "startup", "Reserved": "reserved", "Recovery": "recovery"}


# Built on the list the mount command itself reads, which names every partition by its disk and its number. That list carries each size as
# rounded text ("476.3 GB"), so the bytes here are that text read back: right to within a tenth of a unit, which is enough to draw a disk.
def read_windows_disks(mounted: list[Mounted]) -> list[StorageDisk]:
    entries = [entry for entry in list_devices() if entry.disk_number is not None]
    by_point = {part.mount_point.upper(): part for part in mounted}
    disks: list[StorageDisk] = []
    for number in sorted({entry.disk_number for entry in entries if entry.disk_number is not None}):
        parts = sorted((entry for entry in entries if entry.disk_number == number), key=lambda entry: entry.partition_number or 0)
        regions: list[StorageRegion] = []
        volumes: list[StorageVolume] = []
        for entry in parts:
            amount, _, unit = (entry.size or "0 B").partition(" ")
            size = int(float(amount) * 1024 ** SIZE_UNITS.index(unit))
            # A partition with no letter comes with a placeholder character in the letter's place.
            letter = entry.drive_letter if entry.drive_letter is not None and entry.drive_letter.isalpha() else ""
            role = PARTITION_ROLES.get(entry.extra or "", "")
            regions.append(StorageRegion(id=entry.key, size=size))
            volumes.append(
                plain_volume(
                    identifier=entry.key, device=entry.device_path, name=entry.label or "", role=role, file_system=(entry.fs_type or "").lower(), region=entry.key, size=size,
                    mounted=by_point.get(f"""{letter}:\\""") if letter != "" else None, encrypted=False, locked=False, helper=role in HELPER_ROLES and letter == "",
                    in_use=False, mount_query=entry.key,
                )
            )
        plugged = any(part.removable for part in mounted if part.mount_point in {volume["mount_point"] for volume in volumes})
        disks.append(
            StorageDisk(
                id=f"""Disk {number}""", device=f"""Disk {number}""", name="", place="external" if plugged else "internal", removable=plugged, connection="", solid_state=False,
                health="unknown", size=sum(region["size"] for region in regions), image_file="", can_eject=False, regions=regions, volumes=volumes,
            )
        )
    return disks
