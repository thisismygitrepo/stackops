from typing import cast

from stackops.scripts.python.helpers.helpers_webui.machine_devices_model import StorageVolume, VolumeRole
from stackops.scripts.python.helpers.helpers_webui.machine_devices_mounts import Mounted, read_usage

type Record = dict[str, object]


# What the system's own tools print about disks arrives as untyped records. A key that is missing, empty or of another type reads as nothing.
# lsblk writes numbers and flags as text in its older versions, so both forms are read.
def text_of(record: Record, key: str) -> str:
    value = record.get(key)
    return value if isinstance(value, str) else ""


def number_of(record: Record, key: str) -> int:
    value = record.get(key)
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    return int(value) if isinstance(value, str) and value.isdigit() else 0


def flag_of(record: Record, key: str) -> bool:
    value = record.get(key)
    return value is True or value == "1"


def records_of(record: Record, key: str) -> list[Record]:
    value = record.get(key)
    return [cast(Record, item) for item in cast(list[object], value) if isinstance(item, dict)] if isinstance(value, list) else []


# A volume that is the only thing in its part of the disk: how full it is and whether it can be written come from its mount, when it has one.
def plain_volume(
    identifier: str, device: str, name: str, role: VolumeRole, file_system: str, region: str, size: int, mounted: Mounted | None, encrypted: bool, locked: bool,
    helper: bool, in_use: bool, mount_query: str | None,
) -> StorageVolume:
    usage = read_usage(mounted.mount_point) if mounted is not None else None
    return StorageVolume(
        id=identifier, device=device, name=name, role=role, file_system=file_system, region=region, pool="", size=size, used=usage.used if usage is not None else None,
        free=usage.free if usage is not None else None, mount_point=mounted.mount_point if mounted is not None else "", read_only=mounted is not None and mounted.read_only,
        encrypted=encrypted, locked=locked, helper=helper, in_use=in_use, home=False, answering=True, mount_query=mount_query, actions=[],
    )
