import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import assert_never

from stackops.utils.installer_utils.linux_package_manager import (
    LinuxPackageManager,
    build_metadata_refresh_command,
    build_package_install_command,
    detect_current_linux_distribution,
    get_openssh_server_package,
)


@dataclass(frozen=True, slots=True)
class SshServiceCommands:
    status: tuple[str, ...]
    enable_and_start: str
    restart: str


def run_cmd(cmd: list[str]) -> tuple[bool, str]:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return result.returncode == 0, result.stdout.strip()
    except FileNotFoundError:
        return False, ""


def check_sshd_installed() -> tuple[bool, str]:
    sshd_paths = ["/usr/sbin/sshd", "/usr/bin/sshd", "/sbin/sshd"]
    for path in sshd_paths:
        if Path(path).exists():
            return True, path
    ok, which_out = run_cmd(["which", "sshd"])
    if ok and which_out:
        return True, which_out
    return False, ""


def detect_package_manager() -> tuple[LinuxPackageManager, str]:
    package_manager = detect_current_linux_distribution().package_manager
    openssh_package = get_openssh_server_package(package_manager)
    install_command = shlex.join(("sudo", *build_package_install_command(package_manager, (openssh_package,))))
    match package_manager:
        case "apk":
            return package_manager, install_command
        case "apt":
            refresh_command = shlex.join(("sudo", *build_metadata_refresh_command(package_manager)))
            return package_manager, f"{refresh_command} && {install_command}"
        case "dnf":
            return package_manager, install_command
        case "pacman":
            return package_manager, install_command
    assert_never(package_manager)


def get_ssh_service_commands(package_manager: LinuxPackageManager, service_name: str) -> SshServiceCommands:
    match package_manager:
        case "apk":
            return SshServiceCommands(
                status=("rc-service", service_name, "status"),
                enable_and_start=f"sudo rc-update add {service_name} default && sudo rc-service {service_name} start",
                restart=f"sudo rc-service {service_name} restart",
            )
        case "apt" | "dnf" | "pacman":
            return SshServiceCommands(
                status=("systemctl", "is-active", service_name),
                enable_and_start=f"sudo systemctl enable --now {service_name}",
                restart=f"sudo systemctl restart {service_name}",
            )
    assert_never(package_manager)
