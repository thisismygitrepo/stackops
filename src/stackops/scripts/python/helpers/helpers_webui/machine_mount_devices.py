import os
import platform
import shutil
import sys

from stackops.scripts.python.helpers.helpers_devops.mount_helpers.devices import list_devices
from stackops.scripts.python.helpers.helpers_webui.machine_mount_linux import LinuxTools, describe_linux_devices, read_unlocked_places
from stackops.scripts.python.helpers.helpers_webui.machine_mount_macos import describe_macos_devices, read_macos_layout
from stackops.scripts.python.helpers.helpers_webui.machine_mount_model import MountPicture, MountProblem
from stackops.scripts.python.helpers.helpers_webui.machine_mount_windows import describe_windows_devices, read_free_letters


def _is_elevated() -> bool:
    if sys.platform == "win32":
        import ctypes

        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    return os.geteuid() == 0


# The command's own device list, the one `list-devices` prints, with what each system adds to say whether and how a device can be mounted.
# A system the command does not know answers 501. A listing tool that is missing or fails answers 500 with what it said.
def read_mount_picture() -> MountPicture | MountProblem:
    system = platform.system()
    try:
        match system:
            case "Darwin":
                return {"system": "Darwin", "elevated": _is_elevated(), "letters": [], "devices": describe_macos_devices(entries=list_devices(), layout=read_macos_layout())}
            case "Linux":
                root = _is_elevated()
                tools = LinuxTools(
                    root=root, sudo=shutil.which("sudo") is not None, dislocker=shutil.which("dislocker") is not None, udisksctl=shutil.which("udisksctl") is not None
                )
                return {"system": "Linux", "elevated": root, "letters": [], "devices": describe_linux_devices(entries=list_devices(), tools=tools, unlocked=read_unlocked_places())}
            case "Windows":
                elevated = _is_elevated()
                return {"system": "Windows", "elevated": elevated, "letters": read_free_letters(), "devices": describe_windows_devices(entries=list_devices(), elevated=elevated)}
            case _:
                return MountProblem(status=501, message=f"""StackOps mounts devices on macOS, Linux and Windows. This system is {system or "unknown"}.""")
    except (RuntimeError, OSError) as error:
        return MountProblem(status=500, message=str(error))
