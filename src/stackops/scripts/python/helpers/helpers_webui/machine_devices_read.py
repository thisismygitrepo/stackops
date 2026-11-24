import platform

from stackops.scripts.python.helpers.helpers_webui.machine_devices_linux import read_linux_disks
from stackops.scripts.python.helpers.helpers_webui.machine_devices_macos import read_macos_disks
from stackops.scripts.python.helpers.helpers_webui.machine_devices_model import Place, StoragePicture, StorageProblem
from stackops.scripts.python.helpers.helpers_webui.machine_devices_mounts import apply_rules, read_mounted, read_shares, storage_mark
from stackops.scripts.python.helpers.helpers_webui.machine_devices_windows import read_windows_disks

PLACE_ORDER: dict[Place, int] = {"internal": 0, "external": 1, "image": 2}


# Every disk of this machine with what is on it, and the shares mounted from other computers. The mark is taken before the disks are read,
# so a disk plugged in while that read is under way leaves the picture with an old mark and the page reads again.
# Unmounting and ejecting are only offered on macOS, the one system they were built and tried on.
def read_storage() -> StoragePicture | StorageProblem:
    mounted = read_mounted()
    mark = storage_mark(mounted)
    system = platform.system()
    try:
        match system:
            case "Darwin":
                disks = read_macos_disks(mounted)
            case "Linux":
                disks = read_linux_disks(mounted)
            case "Windows":
                disks = read_windows_disks(mounted)
            case _:
                return StorageProblem(reason="unsupported", message=f"""StackOps does not know how to list disks on {system}.""")
    except FileNotFoundError as error:
        return StorageProblem(reason="tool_missing", message=f"""This system has no {error.filename}, the program StackOps reads its disks with.""")
    except RuntimeError as error:
        return StorageProblem(reason="failed", message=str(error))
    apply_rules(disks=disks, acts=system == "Darwin")
    disks.sort(key=lambda disk: PLACE_ORDER[disk["place"]])
    return StoragePicture(platform="macOS" if system == "Darwin" else system, disks=disks, shares=read_shares(mounted), mark=mark)
