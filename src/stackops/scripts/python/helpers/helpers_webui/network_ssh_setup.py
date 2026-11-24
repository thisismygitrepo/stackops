import os
import platform
import shlex
from typing import TypedDict

from stackops.utils.installer_utils.linux_package_manager import (
    build_package_install_command,
    detect_current_linux_distribution,
    get_openssh_server_package,
    get_openssh_service_name,
)
from stackops.utils.ssh_utils.server_install import build_linux_ssh_server_install_script, build_macos_ssh_server_install_script
from stackops.utils.ssh_utils.windows_server_install import build_windows_ssh_server_install_script


class SetupStep(TypedDict):
    title: str
    detail: str


# What `devops network ssh install-server` would do on this machine, read from the script the command itself runs and never run from here.
# `blocker` is why it cannot work on this machine at all; `password` is who has to approve it.
class SetupPlan(TypedDict):
    system: str
    installs: str
    steps: list[SetupStep]
    notes: list[str]
    password: str
    script: str
    blocker: str


def read_setup_plan() -> SetupPlan:
    system = platform.system()
    plan: SetupPlan = {"system": system, "installs": "", "steps": [], "notes": [], "password": "", "script": "", "blocker": ""}
    if system == "Darwin":
        return {
            **plan,
            "system": "macOS",
            "installs": "Nothing. macOS comes with the SSH server.",
            "steps": [
                {"title": "Look at Remote Login", "detail": "Reads whether the switch is already on. If it is, nothing changes."},
                {"title": "Turn Remote Login on", "detail": "The same switch as System Settings, General, Sharing, Remote Login. It stays on after a restart."},
                {"title": "Check that it stuck", "detail": "Reads the switch again and stops with an error if it is still off."},
            ],
            "notes": [
                "macOS lets only an app with Full Disk Access flip this switch. If it refuses, turn Remote Login on in System Settings yourself.",
                "Nothing is done to the firewall. The checks above say whether it lets connections in.",
            ],
            "password": "Your password, once, because this changes a system setting.",
            "script": build_macos_ssh_server_install_script(),
        }
    if system == "Windows":
        return {
            **plan,
            "installs": "The OpenSSH Server feature of Windows, if it is not there yet.",
            "steps": [
                {"title": "Add the OpenSSH Server feature", "detail": "Skipped when Windows already has it. Windows may ask for a restart first."},
                {"title": "Start the sshd service", "detail": "And set it to start with Windows."},
                {"title": "Open the firewall for it", "detail": "Replaces the rule named OpenSSH-Server-In-TCP with one that lets port 22 in on every network profile."},
                {"title": "Check the result", "detail": "Reads the service and the firewall rule back, and stops with an error if another rule still blocks port 22."},
            ],
            "notes": ["This works only when StackOps itself was started as Administrator."],
            "password": "Nothing, but StackOps has to be running as Administrator.",
            "script": build_windows_ssh_server_install_script(),
        }
    if system != "Linux":
        return {**plan, "blocker": f"""StackOps cannot set up an SSH server on {system or "this system"}."""}
    try:
        distribution = detect_current_linux_distribution()
    except (OSError, RuntimeError, ValueError) as error:
        return {**plan, "blocker": str(error)}
    manager = distribution.package_manager
    package = get_openssh_server_package(manager)
    service = get_openssh_service_name(manager)
    install = shlex.join(build_package_install_command(manager, (package,)))
    is_root = os.geteuid() == 0
    return {
        **plan,
        "installs": f"""The package {package}, with {manager}.""",
        "steps": [
            {"title": f"""Install {package}""", "detail": f"""Runs {install}. A package that is already there is left as it is."""},
            {"title": f"""Start the {service} service""", "detail": "And set it to start with the machine, through systemd, OpenRC or SysV, whichever this machine uses."},
            {"title": "Check that it runs", "detail": "Asks the service manager and stops with an error if the service is not running."},
        ],
        "notes": ["Nothing is done to the firewall. The checks above say whether it lets connections in."],
        "password": "Nothing, because StackOps runs as root here." if is_root else "Your password for sudo, because this installs a package and starts a service.",
        "script": build_linux_ssh_server_install_script(distribution),
    }
