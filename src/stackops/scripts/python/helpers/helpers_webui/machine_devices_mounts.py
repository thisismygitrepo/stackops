import hashlib
import os
import platform
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import psutil

from stackops.scripts.python.helpers.helpers_webui.machine_devices_model import StorageDisk, StorageVolume

SHARE_FILE_SYSTEMS: frozenset[str] = frozenset(
    {"smbfs", "cifs", "smb3", "nfs", "nfs4", "afpfs", "webdav", "davfs", "sshfs", "fuse.sshfs", "fuse.rclone", "macfuse", "osxfuse", "virtiofs", "vboxsf", "9p"}
)
SHARE_ANSWER_SECONDS = 1.5
MACOS_SYSTEM_MOUNTS = "/System/Volumes/"


@dataclass(frozen=True)
class Mounted:
    device: str
    mount_point: str
    file_system: str
    read_only: bool
    remote: bool
    removable: bool


@dataclass(frozen=True)
class Usage:
    total: int
    used: int
    free: int


def read_mounted() -> list[Mounted]:
    return [
        Mounted(
            device=part.device, mount_point=part.mountpoint, file_system=part.fstype.lower(), read_only="ro" in part.opts.split(","),
            remote="remote" in part.opts.split(",") or part.fstype.lower() in SHARE_FILE_SYSTEMS, removable="removable" in part.opts.split(","),
        )
        for part in psutil.disk_partitions(all=True)
    ]


def read_usage(mount_point: str) -> Usage | None:
    try:
        usage = psutil.disk_usage(mount_point)
    except OSError:
        return None
    return Usage(total=usage.total, used=usage.used, free=usage.free)


# What changes when a disk is plugged in, taken out, mounted or unmounted, as one short text. Reading it costs next to nothing, so the page
# asks for it every few seconds and reads the whole picture again only when it differs.
def storage_mark(mounted: list[Mounted]) -> str:
    match platform.system():
        case "Darwin":
            nodes = sorted(name for name in os.listdir("/dev") if name.startswith("disk"))
        case "Linux":
            nodes = Path("/proc/partitions").read_text(encoding="utf-8").split()
        case _:
            nodes = []
    seen = repr((nodes, sorted((part.device, part.mount_point, part.read_only) for part in mounted)))
    return hashlib.sha256(seen.encode(encoding="utf-8")).hexdigest()[:16]


# What is mounted from another computer or by a program, and is no disk of this machine: a disk that a program mounts is listed with its disk.
# A share whose server went away keeps its mount, and asking how full it is then waits for minutes. Each share is asked on a thread of its own
# and the ones that have not answered in time are shown as not answering. The threads are daemons, so one that never returns does not hold
# the server open when it stops.
def read_shares(mounted: list[Mounted]) -> list[StorageVolume]:
    remote = [part for part in mounted if part.remote and not part.device.startswith("/dev/")]
    answers: dict[str, Usage | None] = {}

    def ask(point: str) -> None:
        answers[point] = read_usage(point)

    workers = [threading.Thread(target=ask, args=(part.mount_point,), daemon=True) for part in remote]
    for worker in workers:
        worker.start()
    deadline = time.monotonic() + SHARE_ANSWER_SECONDS
    for worker in workers:
        worker.join(timeout=max(deadline - time.monotonic(), 0))
    shares: list[StorageVolume] = []
    for part in remote:
        usage = answers.get(part.mount_point)
        shares.append(
            StorageVolume(
                id=part.mount_point, device=part.device, name=Path(part.mount_point).name or part.mount_point, role="", file_system=part.file_system, region="", pool="",
                size=usage.total if usage is not None else 0, used=usage.used if usage is not None else None, free=usage.free if usage is not None else None,
                mount_point=part.mount_point, read_only=part.read_only, encrypted=False, locked=False, helper=False, in_use=False, home=False, answering=usage is not None,
                mount_query=None, actions=[],
            )
        )
    return shares


# Marks what the running system lives on, and from that what this page may unmount or eject. `acts` says whether this system's volumes can be
# mounted and unmounted from here at all. A volume in use is never offered for unmounting, and a disk holding one is never offered for ejecting.
# macOS gives its read-only system volume and the volume with everyone's files the same device number, so the home folder is put on the one
# of them that can be written.
def apply_rules(disks: list[StorageDisk], acts: bool) -> None:
    root = Path(f"""{os.environ["SystemDrive"]}\\""") if platform.system() == "Windows" else Path("/")
    home_device = os.stat(Path.home()).st_dev
    system_devices = {home_device, os.stat(root).st_dev, os.stat(sys.prefix).st_dev}
    for disk in disks:
        for volume in disk["volumes"]:
            point = volume["mount_point"]
            if point != "":
                try:
                    device = os.stat(point).st_dev
                except OSError:
                    device = -1
                volume["home"] = device == home_device and not volume["read_only"]
                volume["in_use"] = volume["in_use"] or device in system_devices or point.startswith(MACOS_SYSTEM_MOUNTS)
            if not acts or volume["helper"] or volume["in_use"]:
                continue
            if point != "":
                volume["actions"] = ["unmount"]
            elif not volume["locked"] and volume["file_system"] != "":
                volume["actions"] = ["mount"]
        disk["can_eject"] = acts and disk["place"] != "internal" and not any(volume["in_use"] for volume in disk["volumes"])
