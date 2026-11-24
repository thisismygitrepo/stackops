import plistlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import cast

from stackops.scripts.python.helpers.helpers_devops.mount_helpers.commands import ensure_ok, run_command
from stackops.scripts.python.helpers.helpers_webui.machine_devices_model import HELPER_ROLES, Health, Place, StorageDisk, StorageRegion, StorageVolume, VolumeRole
from stackops.scripts.python.helpers.helpers_webui.machine_devices_mounts import Mounted
from stackops.scripts.python.helpers.helpers_webui.machine_devices_records import Record, flag_of, number_of, plain_volume, records_of, text_of

POOL_ROLES: dict[str, VolumeRole] = {
    "System": "system", "Data": "data", "Preboot": "startup", "Prelogin": "startup", "Recovery": "recovery", "VM": "swap", "Update": "update", "Installer": "update",
    "xART": "firmware", "Hardware": "firmware", "Baseband": "firmware", "Sidecar": "firmware", "Backup": "backup",
}
SLICE_ROLES: dict[str, VolumeRole] = {
    "EFI": "startup", "Apple_Boot": "recovery", "Apple_APFS_ISC": "firmware", "Apple_APFS_Recovery": "recovery", "Windows Recovery": "recovery", "Linux Swap": "swap",
    "Microsoft Reserved": "reserved", "Apple_partition_map": "reserved", "Apple_KernelCoreDump": "reserved",
}
SMART_HEALTH: dict[str, Health] = {"Verified": "good", "Failing": "failing"}
DETAIL_WORKERS = 8


def _plist(arguments: list[str]) -> Record:
    text = ensure_ok(run_command(arguments), " ".join(arguments[:2]))
    return cast(Record, plistlib.loads(text.encode(encoding="utf-8")))


def _pool_volumes(container: Record, region: str, facts: dict[str, Record], free: int | None, by_point: dict[str, Mounted]) -> list[StorageVolume]:
    listed = records_of(container, "APFSVolumes")
    # The system volume is mounted through a sealed snapshot of itself, which the list also carries as a device of its own. The two are shown
    # as the one volume they are, at the snapshot's mount point: that is "/", the place people know it by.
    snapshots = {text_of(snapshot, "SnapshotBSD") for volume in listed for snapshot in records_of(volume, "MountedSnapshots")}
    volumes: list[StorageVolume] = []
    for volume in listed:
        identifier = text_of(volume, "DeviceIdentifier")
        if identifier in snapshots:
            continue
        fact = facts.get(identifier, {})
        roles = fact.get("Roles")
        first_role = roles[0] if isinstance(roles, list) and roles else ""
        role = POOL_ROLES.get(first_role, "") if isinstance(first_role, str) else ""
        snapshot_points = [text_of(snapshot, "SnapshotMountPoint") for snapshot in records_of(volume, "MountedSnapshots")]
        point = next((candidate for candidate in snapshot_points if candidate != ""), text_of(volume, "MountPoint"))
        mount = by_point.get(point)
        volumes.append(
            StorageVolume(
                id=identifier, device=f"""/dev/{identifier}""", name=text_of(volume, "VolumeName"), role=role, file_system="apfs", region=region,
                pool=text_of(container, "DeviceIdentifier"), size=number_of(container, "Size"), used=number_of(volume, "CapacityInUse"), free=free, mount_point=point,
                read_only=mount is not None and mount.read_only, encrypted=flag_of(fact, "Encryption") or flag_of(fact, "FileVault"), locked=flag_of(fact, "Locked"),
                helper=role in HELPER_ROLES or flag_of(volume, "OSInternal") or flag_of(container, "OSInternal"), in_use=False, home=False, answering=True,
                mount_query=None, actions=[],
            )
        )
    return volumes


def read_macos_disks(mounted: list[Mounted]) -> list[StorageDisk]:
    entries = records_of(_plist(["diskutil", "list", "-plist"]), "AllDisksAndPartitions")
    drives = [entry for entry in entries if not records_of(entry, "APFSPhysicalStores")]
    # A pool of volumes is listed as a disk of its own. Here it goes back under the slice of the real disk that stores it; a pool spread over
    # two slices goes under its first one, and the other is left as a part of the disk with nothing listed in it.
    pools: dict[str, Record | None] = {}
    for entry in entries:
        for position, store in enumerate(records_of(entry, "APFSPhysicalStores")):
            pools[text_of(store, "DeviceIdentifier")] = entry if position == 0 else None
    slices = {text_of(drive, "DeviceIdentifier"): records_of(drive, "Partitions") or [drive] for drive in drives}
    by_device = {part.device: part for part in mounted}
    by_point = {part.mount_point: part for part in mounted}
    # One detail read per disk, and one per slice whose format is not known yet: a mounted slice's format comes with its mount, a pool's is APFS.
    unread = (text_of(part, "DeviceIdentifier") for parts in slices.values() for part in parts)
    asked = sorted({*slices, *(identifier for identifier in unread if identifier not in pools and f"""/dev/{identifier}""" not in by_device)})
    with ThreadPoolExecutor(max_workers=DETAIL_WORKERS) as workers:
        pool_job = workers.submit(_plist, ["diskutil", "apfs", "list", "-plist"])
        image_job = workers.submit(_plist, ["hdiutil", "info", "-plist"])
        details = dict(zip(asked, workers.map(lambda identifier: _plist(["diskutil", "info", "-plist", identifier]), asked)))
        containers = records_of(pool_job.result(), "Containers")
        images = records_of(image_job.result(), "images")
    pool_free = {text_of(container, "ContainerReference"): number_of(container, "CapacityFree") for container in containers}
    pool_facts = {text_of(volume, "DeviceIdentifier"): volume for container in containers for volume in records_of(container, "Volumes")}
    image_files = {text_of(entity, "dev-entry").removeprefix("/dev/"): text_of(image, "image-path") for image in images for entity in records_of(image, "system-entities")}

    disks: list[StorageDisk] = []
    for drive in drives:
        identifier = text_of(drive, "DeviceIdentifier")
        detail = details[identifier]
        image_file = image_files.get(identifier, "")
        is_image = text_of(detail, "BusProtocol") == "Disk Image"
        place: Place = "image" if is_image else "internal" if flag_of(detail, "Internal") else "external"
        volumes: list[StorageVolume] = []
        for part in slices[identifier]:
            part_id = text_of(part, "DeviceIdentifier")
            if part_id in pools:
                pool = pools[part_id]
                if pool is not None:
                    volumes.extend(_pool_volumes(container=pool, region=part_id, facts=pool_facts, free=pool_free.get(text_of(pool, "DeviceIdentifier")), by_point=by_point))
                continue
            role = SLICE_ROLES.get(text_of(part, "Content"), "")
            mount = by_device.get(f"""/dev/{part_id}""")
            # `mount_query` is the slice's own name: the mount command lists every slice of a disk that has slices, and a disk without any as itself.
            volumes.append(
                plain_volume(
                    identifier=part_id, device=f"""/dev/{part_id}""", name=text_of(part, "VolumeName"), role=role,
                    file_system=mount.file_system if mount is not None else text_of(details[part_id], "FilesystemType"), region=part_id, size=number_of(part, "Size"),
                    mounted=mount, encrypted=False, locked=False, helper=role in HELPER_ROLES or flag_of(part, "OSInternal"), in_use=False, mount_query=part_id,
                )
            )
        disks.append(
            StorageDisk(
                id=identifier, device=f"""/dev/{identifier}""", name=Path(image_file).name if image_file != "" else text_of(detail, "MediaName"), place=place,
                removable=flag_of(detail, "RemovableMedia") and not is_image, connection=text_of(detail, "BusProtocol"), solid_state=flag_of(detail, "SolidState"),
                health=SMART_HEALTH.get(text_of(detail, "SMARTStatus"), "unknown"), size=number_of(drive, "Size"), image_file=image_file, can_eject=False,
                regions=[StorageRegion(id=text_of(part, "DeviceIdentifier"), size=number_of(part, "Size")) for part in slices[identifier]], volumes=volumes,
            )
        )
    return disks
