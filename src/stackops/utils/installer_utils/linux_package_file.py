from collections.abc import Sequence
import os
from pathlib import Path
import subprocess
from typing import assert_never

from stackops.utils.installer_utils.linux_package_manager import LinuxPackageManager, detect_current_linux_distribution


class IncompatibleLinuxPackageError(ValueError):
    def __init__(self, *, package_manager: LinuxPackageManager, package_suffix: str) -> None:
        super().__init__(f"{package_suffix or '<no suffix>'} packages cannot be installed with {package_manager}")


def build_linux_package_file_install_command(
    package_manager: LinuxPackageManager, package_path: Path, privilege_prefix: Sequence[str]
) -> tuple[str, ...]:
    package_suffix = package_path.suffix.lower()
    match package_manager:
        case "apt":
            if package_suffix != ".deb":
                raise IncompatibleLinuxPackageError(package_manager=package_manager, package_suffix=package_suffix)
            package_command = ("apt-get", "install", "-y", str(package_path))
        case "dnf":
            if package_suffix != ".rpm":
                raise IncompatibleLinuxPackageError(package_manager=package_manager, package_suffix=package_suffix)
            package_command = ("dnf", "install", "-y", str(package_path))
        case _:
            assert_never(package_manager)
    return (*privilege_prefix, *package_command)


def install_linux_package_file(package_path: Path) -> None:
    distribution = detect_current_linux_distribution()
    privilege_prefix = () if os.geteuid() == 0 else ("sudo",)
    command = build_linux_package_file_install_command(
        package_manager=distribution.package_manager, package_path=package_path, privilege_prefix=privilege_prefix
    )
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Linux package installation failed with exit code {result.returncode}: {result.stderr.strip() or result.stdout.strip()}")
    package_path.unlink()
