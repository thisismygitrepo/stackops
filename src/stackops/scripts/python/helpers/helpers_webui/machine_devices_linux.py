import json
from typing import cast

from stackops.scripts.python.helpers.helpers_devops.mount_helpers.commands import ensure_ok, run_command
from stackops.scripts.python.helpers.helpers_webui.machine_devices_model import HELPER_ROLES, Place, StorageDisk, StorageRegion, StorageVolume, VolumeRole
from stackops.scripts.python.helpers.helpers_webui.machine_devices_mounts import Mounted
from stackops.scripts.python.helpers.helpers_webui.machine_devices_records import Record, flag_of, number_of, plain_volume, records_of, text_of

# Columns lsblk has had since before it could print JSON, so the read works on old systems too.
LSBLK_COLUMNS = "NAME,KNAME,TYPE,SIZE,FSTYPE,LABEL,PARTLABEL,MOUNTPOINT,MODEL,VENDOR,TRAN,RM,HOTPLUG,RO,ROTA"
DISK_TYPES = frozenset({"disk", "loop", "rom"})
MEMORY_DISK_PREFIXES = ("zram", "ram")
LOCKING_FORMATS = frozenset({"crypto_LUKS", "BitLocker"})
# Formats that hold other devices, not files: what is inside them is listed, they are not.
HOLDING_FORMATS = frozenset({"", "LVM2_member", "linux_raid_member", "zfs_member", "bcache"}) | LOCKING_FORMATS
STARTUP_MOUNTS = frozenset({"/boot", "/boot/efi", "/efi"})
ACTIVE_SWAP = "[SWAP]"


def _role(node: Record) -> VolumeRole:
    label = text_of(node, "partlabel").lower()
    if text_of(node, "fstype") == "swap":
        return "swap"
    if text_of(node, "mountpoint") == "/":
        return "system"
    if text_of(node, "mountpoint") in STARTUP_MOUNTS or "efi" in label:
        return "startup"
    return "reserved" if "reserved" in label or "bios boot" in label else ""


# One part of a disk and whatever is stacked on it: an unlocked encrypted partition, the volumes of a volume group, a disk set.
# A device that sits on two disks is listed under each of them by lsblk; `seen` keeps it to the first.
def _volumes(node: Record, region: str, encrypted: bool, by_point: dict[str, Mounted], seen: set[str]) -> list[StorageVolume]:
    kernel_name = text_of(node, "kname")
    if kernel_name in seen:
        return []
    seen.add(kernel_name)
    form = text_of(node, "fstype")
    children = records_of(node, "children")
    inside = [volume for child in children for volume in _volumes(node=child, region=region, encrypted=encrypted or form in LOCKING_FORMATS, by_point=by_point, seen=seen)]
    if children and form in HOLDING_FORMATS:
        return inside
    name = text_of(node, "name")
    point = text_of(node, "mountpoint")
    role = _role(node)
    volume = plain_volume(
        identifier=name, device=f"""/dev/mapper/{name}""" if kernel_name.startswith("dm-") else f"""/dev/{name}""", name=text_of(node, "label") or text_of(node, "partlabel"),
        role=role, file_system=form.lower(), region=region, size=number_of(node, "size"), mounted=by_point.get(point), encrypted=encrypted or form in LOCKING_FORMATS,
        locked=form in LOCKING_FORMATS, helper=role in HELPER_ROLES, in_use=point == ACTIVE_SWAP,
        # The mount command lists plain partitions only, and takes one by its name.
        mount_query=name if text_of(node, "type") == "part" else None,
    )
    return [volume, *inside]


def read_linux_disks(mounted: list[Mounted]) -> list[StorageDisk]:
    text = ensure_ok(run_command(["lsblk", "-J", "-b", "-o", LSBLK_COLUMNS]), "lsblk")
    nodes = records_of(cast(Record, json.loads(text)), "blockdevices")
    by_point = {part.mount_point: part for part in mounted}
    seen: set[str] = set()
    disks: list[StorageDisk] = []
    for node in nodes:
        kind = text_of(node, "type")
        name = text_of(node, "name")
        # Left out: memory-backed swap, empty card readers and drives with no disc, and the read-only package images some systems mount by the dozen.
        if kind not in DISK_TYPES or name.startswith(MEMORY_DISK_PREFIXES) or number_of(node, "size") == 0 or (kind == "loop" and text_of(node, "fstype") == "squashfs"):
            continue
        parts = [child for child in records_of(node, "children") if text_of(child, "type") == "part"]
        regions = parts or [node]
        place: Place = "image" if kind == "loop" else "external" if text_of(node, "tran") == "usb" or flag_of(node, "hotplug") or flag_of(node, "rm") else "internal"
        disks.append(
            StorageDisk(
                id=name, device=f"""/dev/{name}""", name=f"""{text_of(node, "vendor").strip()} {text_of(node, "model").strip()}""".strip(), place=place,
                removable=flag_of(node, "rm"), connection=text_of(node, "tran"), solid_state=kind == "disk" and "rota" in node and not flag_of(node, "rota"),
                health="unknown", size=number_of(node, "size"), image_file="", can_eject=False,
                regions=[StorageRegion(id=text_of(region, "name"), size=number_of(region, "size")) for region in regions],
                volumes=[volume for region in regions for volume in _volumes(node=region, region=text_of(region, "name"), encrypted=False, by_point=by_point, seen=seen)],
            )
        )
    return disks
