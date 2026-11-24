from dataclasses import dataclass
from typing import Literal, TypedDict

type Place = Literal["internal", "external", "image"]
type Health = Literal["good", "failing", "unknown"]
type VolumeRole = Literal["system", "data", "startup", "recovery", "swap", "update", "firmware", "backup", "reserved", ""]
type VolumeAction = Literal["mount", "unmount"]
type ProblemReason = Literal["unsupported", "tool_missing", "refused", "unknown_device", "failed"]

HELPER_ROLES: frozenset[VolumeRole] = frozenset({"startup", "recovery", "swap", "update", "firmware", "reserved"})


# One place that holds files: a partition with a file system, one volume of a shared pool, or a share from another computer.
# `region` is the part of its disk it lives in. Volumes with the same non-empty `pool` share one stretch of free space, so `size` and `free` are
# the pool's and `used` is the volume's own. `used`, `free` and `read_only` are only known while it is mounted, except in a pool.
# `mount_query` is what `utils machine mount --device` accepts for it, or None when that command cannot address it.
class StorageVolume(TypedDict):
    id: str
    device: str
    name: str
    role: VolumeRole
    file_system: str
    region: str
    pool: str
    size: int
    used: int | None
    free: int | None
    mount_point: str
    read_only: bool
    encrypted: bool
    locked: bool
    helper: bool
    in_use: bool
    home: bool
    answering: bool
    mount_query: str | None
    actions: list[VolumeAction]


class StorageRegion(TypedDict):
    id: str
    size: int


class StorageDisk(TypedDict):
    id: str
    device: str
    name: str
    place: Place
    removable: bool
    connection: str
    solid_state: bool
    health: Health
    size: int
    image_file: str
    can_eject: bool
    regions: list[StorageRegion]
    volumes: list[StorageVolume]


class StoragePicture(TypedDict):
    platform: str
    disks: list[StorageDisk]
    shares: list[StorageVolume]
    mark: str


@dataclass(frozen=True)
class StorageProblem:
    reason: ProblemReason
    message: str
