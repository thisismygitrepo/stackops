import os
import shutil
import subprocess
import sys
from collections import Counter
from typing import Final

from rich.console import Console
from rich.text import Text

from stackops.utils.cli_utils.command_lookup import check_tool_exists
from stackops.utils.installer_utils.constants import BULK_INSTALL_SUDO_EXAMPLE_COUNT, SYSTEM_INSTALLER_COMMANDS
from stackops.utils.installer_utils.install_request_logic import (
    InstallTarget,
    build_install_target,
    is_native_linux_package_manager_command,
    resolve_installer_pattern,
    should_skip_install,
)
from stackops.utils.installer_utils.installer_bulk_models import PlannedInstall
from stackops.utils.installer_utils.installer_class import Installer
from stackops.utils.installer_utils.linux_package_file import LINUX_PACKAGE_FILE_SUFFIXES
from stackops.utils.schemas.installer.installer_types import InstallRequest, InstallerData, get_normalized_arch, get_os_name


SYSTEM_PACKAGE_FILE_SUFFIXES: Final[tuple[str, ...]] = (*LINUX_PACKAGE_FILE_SUFFIXES, ".msi", ".dmg")


def holds_system_installer_lock(install_target: InstallTarget) -> bool:
    installer_value = install_target.installer_value
    return (
        install_target.installer_kind == "script"
        or is_native_linux_package_manager_command(installer_value)
        or any(token in SYSTEM_INSTALLER_COMMANDS for token in installer_value.split())
        or installer_value.lower().endswith(SYSTEM_PACKAGE_FILE_SUFFIXES)
    )


def plan_bulk_installs(installers_data: list[InstallerData], install_request: InstallRequest) -> list[PlannedInstall]:
    operating_system = get_os_name()
    architecture = get_normalized_arch()
    planned_installs: list[PlannedInstall] = []
    for installer_data in installers_data:
        exe_name = Installer(installer_data=installer_data).get_exe_name()
        installer_value = resolve_installer_pattern(installer_data=installer_data, operating_system=operating_system, architecture=architecture)
        if installer_value is None:
            raise ValueError(f"""No installation pattern for {exe_name} on {operating_system} {architecture}""")
        system_lock = holds_system_installer_lock(install_target=build_install_target(repo_url=installer_data["repoURL"], installer_value=installer_value))
        was_installed = check_tool_exists(exe_name)
        planned_installs.append(
            PlannedInstall(
                installer_data=installer_data,
                exe_name=exe_name,
                holds_system_installer_lock=system_lock,
                may_need_sudo=system_lock or "sudo" in installer_value.split(),
                was_installed=was_installed,
                skip=should_skip_install(exe_name=exe_name, install_request=install_request, tool_exists=lambda _tool_name: was_installed),
            )
        )
    duplicated_exe_names = [exe_name for exe_name, count in Counter(planned.exe_name for planned in planned_installs).items() if count > 1]
    if len(duplicated_exe_names) > 0:
        raise ValueError(f"""Bulk install received duplicate executables: {", ".join(duplicated_exe_names)}""")
    return planned_installs


def cache_sudo_credentials(planned_installs: list[PlannedInstall], console: Console) -> bool:
    if sys.platform == "win32" or os.geteuid() == 0 or shutil.which("sudo") is None:
        return False
    sudo_names = [planned.exe_name for planned in planned_installs if planned.may_need_sudo]
    if len(sudo_names) == 0:
        return False
    sudo_ready = subprocess.run(["sudo", "-n", "true"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    if sudo_ready.returncode == 0:
        return True
    examples = ", ".join(sudo_names[:BULK_INSTALL_SUDO_EXAMPLE_COUNT]) + (", …" if len(sudo_names) > BULK_INSTALL_SUDO_EXAMPLE_COUNT else "")
    without_sudo = "continuing without it, installers that need sudo will fail."
    try:
        os.close(os.open("/dev/tty", os.O_RDWR | os.O_NOCTTY))
    except OSError:
        console.print(Text(f""" ⚠️  sudo may be needed by {len(sudo_names)} installers ({examples}) but there is no terminal to ask for the password; {without_sudo}""", style="yellow"))
        return False
    console.print(Text(f""" 🔐 sudo may be needed by {len(sudo_names)} installers ({examples}); authenticate once and they run unattended."""))
    if subprocess.run(["sudo", "-v"], stdin=subprocess.DEVNULL, check=False).returncode != 0:
        console.print(Text(f""" ⚠️  sudo authentication failed; {without_sudo}""", style="yellow"))
        return False
    return True
