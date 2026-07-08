import platform
import shlex
from typing import TYPE_CHECKING, Final

from rich import box
from rich.console import Console
from rich.panel import Panel

import stackops.jobs.installer.linux_scripts as linux_scripts
import stackops.jobs.installer.powershell_scripts as powershell_scripts
from stackops.utils.installer_utils.installer_main_protocol import InstallerPythonScriptMain
from stackops.utils.installer_utils.linux_package_manager import (
    LinuxDistribution,
    build_metadata_refresh_command,
    build_package_install_command,
    detect_current_linux_distribution,
)
from stackops.utils.schemas.installer.installer_types import InstallerData
from stackops.utils.path_reference import get_path_reference_path


APT_PACKAGES: Final[tuple[str, ...]] = (
    "curl",
    "wget",
    "gpg",
    "lsb-release",
    "apt-transport-https",
    "samba",
    "fuse3",
    "nfs-common",
    "git",
    "net-tools",
    "htop",
    "nano",
    "build-essential",
    "python3-dev",
    "unzip",
    "pkg-config",
    "libssl-dev",
)
APK_PACKAGES: Final[tuple[str, ...]] = (
    "bash",
    "ca-certificates",
    "curl",
    "wget",
    "gnupg",
    "lsb-release-minimal",
    "samba",
    "fuse3",
    "nfs-utils",
    "git",
    "net-tools",
    "htop",
    "nano",
    "build-base",
    "python3-dev",
    "unzip",
    "pkgconf",
    "openssl-dev",
    "libstdc++",
)
DNF_PACKAGES: Final[tuple[str, ...]] = (
    "curl",
    "wget",
    "gnupg2",
    "samba",
    "fuse3",
    "nfs-utils",
    "git",
    "net-tools",
    "nano",
    "gcc",
    "gcc-c++",
    "make",
    "python3-devel",
    "unzip",
    "pkgconf-pkg-config",
    "openssl-devel",
)
PACMAN_PACKAGES: Final[tuple[str, ...]] = (
    "curl",
    "wget",
    "gnupg",
    "lsb-release",
    "samba",
    "fuse3",
    "nfs-utils",
    "git",
    "net-tools",
    "htop",
    "nano",
    "base-devel",
    "python",
    "unzip",
    "pkgconf",
    "openssl",
)


def _build_linux_install_script(distribution: LinuxDistribution) -> str:
    match distribution.package_manager:
        case "apk":
            packages = APK_PACKAGES
        case "apt":
            packages = APT_PACKAGES
        case "dnf":
            packages = DNF_PACKAGES
        case "pacman":
            packages = PACMAN_PACKAGES

    refresh_command = build_metadata_refresh_command(distribution.package_manager)
    install_command = build_package_install_command(distribution.package_manager, packages)
    return "\n".join(
        (
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            shlex.join(("sudo", *refresh_command)),
            shlex.join(("sudo", *install_command)),
            "curl -fsSL https://bun.com/install | bash",
            'sudo ln -sfn "$HOME/.bun/bin/bun" /usr/local/bin/node',
            "",
        )
    )


def main(installer_data: InstallerData, version: str | None, update: bool) -> None:
    console = Console()
    _ = installer_data, update
    operating_system = platform.system()
    console.print(
        Panel.fit(
            "\n".join([f"💻 Platform: {operating_system}", f"🔄 Version: {'latest' if version is None else version}"]),
            title="🔧 ABC Installer",
            border_style="blue",
            box=box.ROUNDED,
        )
    )

    if operating_system == "Windows":
        console.print("🪟 Installing ABC on Windows using winget...", style="bold")
        script = get_path_reference_path(module=powershell_scripts, path_reference=powershell_scripts.SYSABC_PATH_REFERENCE)
        program = script.read_text(encoding="utf-8")
    elif operating_system == "Linux":
        distribution = detect_current_linux_distribution()
        console.print(f"🐧 Installing ABC on {distribution.distribution_id} using {distribution.package_manager}...", style="bold")
        program = _build_linux_install_script(distribution)
    elif operating_system == "Darwin":
        console.print("🍎 Installing ABC on macOS...", style="bold")
        script = get_path_reference_path(module=linux_scripts, path_reference=linux_scripts.SYSABC_MACOS_PATH_REFERENCE)
        program = script.read_text(encoding="utf-8")
    else:
        error_msg = f"Unsupported platform: {operating_system}"
        console.print(Panel.fit("\n".join([error_msg]), title="❌ Error", subtitle="⚠️ Unsupported platform", border_style="red", box=box.ROUNDED))
        raise NotImplementedError(error_msg)
    from stackops.utils.code import run_shell_script
    from stackops.utils.meta import print_code

    print_code(code=program, lexer="shell", desc="Installation Script Preview")
    result = run_shell_script(program, display_script=True, clean_env=False)
    if result.returncode != 0:
        raise RuntimeError(f"ABC installation failed with exit code {result.returncode}")


if __name__ == "__main__":
    if TYPE_CHECKING:
        _main_protocol_check: InstallerPythonScriptMain = main
