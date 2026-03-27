import getpass
import json
import os
import tempfile
from pathlib import Path
from typing import Literal, TypeAlias, cast

from machineconfig.scripts.python.helpers.helpers_devops.mount_helpers.commands import ensure_ok, run_command, run_command_sudo

MountBackend: TypeAlias = Literal["mount", "dislocker", "udisksctl"]
from machineconfig.scripts.python.helpers.helpers_devops.mount_helpers.device_entry import DeviceEntry
from machineconfig.scripts.python.helpers.helpers_devops.mount_helpers.selection import pick_device
from machineconfig.scripts.python.helpers.helpers_devops.mount_helpers.utils import as_str


def _flatten_lsblk_devices(devices: list[dict[str, object]]) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    stack = list(devices)
    while stack:
        item = stack.pop(0)
        result.append(item)
        children = item.get("children")
        if isinstance(children, list):
            for child in children:
                if isinstance(child, dict):
                    stack.append(cast(dict[str, object], child))
    return result


def list_linux_devices() -> list[DeviceEntry]:
    result = run_command(["lsblk", "-J", "-o", "NAME,SIZE,TYPE,FSTYPE,LABEL,MOUNTPOINT,UUID,MODEL"])
    text = ensure_ok(result, "lsblk")
    data = json.loads(text)
    raw_devices = data.get("blockdevices")
    entries: list[DeviceEntry] = []
    if isinstance(raw_devices, list):
        for item in _flatten_lsblk_devices(raw_devices):
            name_value = item.get("name")
            if not isinstance(name_value, str):
                continue
            device_type = item.get("type")
            if not isinstance(device_type, str):
                continue
            if device_type not in {"disk", "part"}:
                continue
            device_path = f"/dev/{name_value}"
            label = as_str(item.get("label"))
            mount_point = as_str(item.get("mountpoint"))
            fs_type = as_str(item.get("fstype"))
            size = as_str(item.get("size"))
            model = as_str(item.get("model"))
            entries.append(
                DeviceEntry(
                    platform_name="Linux",
                    key=name_value,
                    device_path=device_path,
                    device_type=device_type,
                    label=label,
                    mount_point=mount_point,
                    fs_type=fs_type,
                    size=size,
                    extra=model,
                    disk_number=None,
                    partition_number=None,
                    drive_letter=None,
                )
            )
    return entries

def is_admin() -> bool:
    try:
        return os.geteuid() == 0
    except AttributeError:
        # Use Windows API via ctypes or other method here
        return False

def _find_crypt_device(part_name: str) -> str | None:
    result = run_command(["lsblk", "-rno", "PATH,TYPE,PKNAME"])
    for line in result.stdout.splitlines():
        cols = line.split()
        if len(cols) == 3 and cols[1] == "crypt" and cols[2] == part_name:
            return cols[0]
    return None


def _mount_udisksctl_linux(device_path: str, read_only: bool) -> None:
    part_name = Path(device_path).name
    map_dev = _find_crypt_device(part_name)
    if map_dev is not None:
        check = run_command(["findmnt", "-rn", map_dev])
        if check.returncode == 0:
            target = run_command(["findmnt", "-nro", "TARGET", map_dev])
            print(f"Already mounted: {map_dev} at {target.stdout.strip()}")
            return
    print(f"Unlocking {device_path}...")
    unlock_cmd = ["udisksctl", "unlock", "-b", device_path]
    if read_only:
        unlock_cmd.append("--read-only")
    ensure_ok(run_command(unlock_cmd), "udisksctl unlock")
    map_dev = _find_crypt_device(part_name)
    if map_dev is None:
        raise RuntimeError("Could not find mapped cleartext device after unlock")
    print(f"Mounting {map_dev}...")
    result = run_command(["udisksctl", "mount", "-b", map_dev])
    ensure_ok(result, "udisksctl mount")
    print(result.stdout.strip())


def _mount_bitlocker_linux(device_path: str, mount_point: str, read_only: bool) -> None:
    print("🔒 BitLocker volume detected.")
    method = input("Unlock method?\n  [1] Paste password\n  [2] Path to recovery key / BEK file\nChoice [1]: ").strip() or "1"
    dislocker_dir = Path(tempfile.mkdtemp(prefix="dislocker_"))
    ro_flags = ["-r"] if read_only else []
    if method == "2":
        key_file = input("Path to key file: ").strip()
        dislocker_cmd = ["dislocker", *ro_flags, device_path, "-f", key_file, "--", str(dislocker_dir)]
    else:
        password = getpass.getpass("BitLocker password: ")
        dislocker_cmd = ["dislocker", *ro_flags, device_path, f"-u{password}", "--", str(dislocker_dir)]
    result = run_command_sudo(dislocker_cmd)
    ensure_ok(result, "dislocker")
    mount_path = Path(mount_point)
    try:
        mount_path.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        ensure_ok(run_command_sudo(["mkdir", "-p", str(mount_path)]), "mkdir")
    dislocker_file = dislocker_dir / "dislocker-file"
    loop_opts = "loop,ro" if read_only else "loop"
    result = run_command_sudo(["mount", "-o", loop_opts, str(dislocker_file), str(mount_path)])
    ensure_ok(result, "mount (dislocker-file)")
    print(f"🔓 BitLocker volume mounted at {mount_point} (dislocker temp dir: {dislocker_dir})")


def mount_linux(entry: DeviceEntry, mount_point: str, read_only: bool, backend: MountBackend) -> None:
    if backend == "udisksctl":
        _mount_udisksctl_linux(entry.device_path, read_only)
        return
    if backend == "dislocker":
        _mount_bitlocker_linux(entry.device_path, mount_point, read_only)
        return
    # backend == "mount"
    if entry.mount_point is not None and entry.mount_point != "":
        print(f"Already mounted at {entry.mount_point}")
        return
    mount_path = Path(mount_point)
    try:
        mount_path.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        mkdir_result = run_command_sudo(["mkdir", "-p", str(mount_path)])
        ensure_ok(mkdir_result, "mkdir")
    mount_opts = ["-o", "ro"] if read_only else []
    if os.geteuid() == 0:
        result = run_command(["mount", *mount_opts, entry.device_path, str(mount_path)])
    else:
        result = run_command_sudo(["mount", *mount_opts, entry.device_path, str(mount_path)])
    if result.returncode != 0:
        err = (result.stderr + result.stdout).lower()
        if "bitlocker" in err:
            _mount_bitlocker_linux(entry.device_path, mount_point, read_only)
            return
        ensure_ok(result, "mount")


def _is_partition_of_disk(partition: DeviceEntry, disk: DeviceEntry) -> bool:
    if partition.device_type != "part" or disk.device_type != "disk":
        return False
    if partition.key == disk.key:
        return False
    if not partition.key.startswith(disk.key):
        return False
    return True


def select_linux_partition(entries: list[DeviceEntry], entry: DeviceEntry) -> DeviceEntry:
    if entry.device_type != "disk":
        return entry
    candidates = [device for device in entries if _is_partition_of_disk(device, entry)]
    with_fs = [device for device in candidates if device.fs_type is not None and device.fs_type != ""]
    if len(with_fs) == 1:
        return with_fs[0]
    if len(with_fs) > 1:
        return pick_device(with_fs, header="Select partition to mount")
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        return pick_device(candidates, header="Select partition to mount")
    raise RuntimeError("No mountable partitions found for selected disk")
