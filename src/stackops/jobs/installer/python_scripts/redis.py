"""redis installer"""

import platform
import subprocess
from typing import TYPE_CHECKING

from rich import box
from rich.console import Console
from rich.panel import Panel

from stackops.utils.installer_utils.installer_main_protocol import InstallerPythonScriptMain
from stackops.utils.installer_utils.linux_package_manager import LinuxDistribution, detect_current_linux_distribution
from stackops.utils.schemas.installer.installer_types import InstallerData


def _build_linux_install_script(distribution: LinuxDistribution) -> str:
    match distribution.package_manager:
        case "apk":
            repository_setup = """
echo "📦 Using Alpine Linux's official repositories..."
""".strip()
            install_command = "sudo apk add --no-cache redis"
            service_setup = """sudo rc-update add redis default
sudo rc-service redis start"""
        case "apt":
            repository_setup = """
echo "📥 Installing APT repository prerequisites..."
sudo apt-get update
sudo apt-get install -y lsb-release curl gpg

echo "🔐 Adding Redis's official signing key..."
curl -fsSL https://packages.redis.io/gpg | sudo gpg --yes --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg
sudo chmod 644 /usr/share/keyrings/redis-archive-keyring.gpg

echo "📝 Adding Redis's official APT repository..."
echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/redis.list > /dev/null
sudo apt-get update
"""
            install_command = "sudo apt-get install -y redis"
            service_setup = "sudo systemctl enable --now redis-server"
        case "dnf":
            repository_setup = """
echo "🔄 Refreshing DNF package metadata..."
sudo dnf makecache --refresh
"""
            install_command = "sudo dnf install -y redis"
            service_setup = "sudo systemctl enable --now redis"
        case "pacman":
            repository_setup = """
echo "📦 Using Arch Linux's official repositories..."
""".strip()
            install_command = "sudo pacman -S --needed --noconfirm valkey"
            service_setup = "sudo systemctl enable --now redis"

    return f"""#!/usr/bin/env bash
set -euo pipefail

echo "🗃️ Installing Redis on {distribution.distribution_id} with {distribution.package_manager}"
{repository_setup}

echo "📦 Installing Redis..."
{install_command}

echo "⚙️ Enabling and starting Redis..."
{service_setup}

echo "🧪 Testing Redis..."
redis-cli ping

echo "✅ Redis installation completed"
"""


def main(installer_data: InstallerData, version: str | None, update: bool) -> None:
    console = Console()
    _ = installer_data, update
    system = platform.system()
    console.print(
        Panel.fit(
            "\n".join([f"💻 Platform: {system}", f"🔄 Version: {'latest' if version is None else version}"]),
            title="🗃️  Redis Installer",
            border_style="red",
            box=box.ROUNDED,
        )
    )

    match system:
        case "Windows":
            error_msg = "Redis installation not supported on Windows through this installer"
            console.print(
                Panel.fit(
                    "\n".join([error_msg, "💡 Consider using WSL2 or Docker to run Redis on Windows"]),
                    title="❌ Error",
                    subtitle="⚠️ Unsupported platform",
                    border_style="red",
                    box=box.ROUNDED,
                )
            )
            raise NotImplementedError(error_msg)
        case "Linux":
            distribution = detect_current_linux_distribution()
            console.print(f"🐧 Installing Redis on {distribution.distribution_id} with {distribution.package_manager}...", style="bold")
            program = _build_linux_install_script(distribution)
        case "Darwin":
            console.print("🍎 Installing Redis on macOS using Homebrew...", style="bold")
            program = "brew install redis"
        case _:
            error_msg = f"Unsupported platform: {system}"
            console.print(Panel.fit(error_msg, title="❌ Error", subtitle="⚠️ Unsupported platform", border_style="red", box=box.ROUNDED))
            raise NotImplementedError(error_msg)

    subprocess.run(["bash", "-c", program], text=True, check=True)
    console.print("✅ Redis installation completed successfully", style="bold green")


if __name__ == "__main__":
    if TYPE_CHECKING:
        _main_protocol_check: InstallerPythonScriptMain = main
    pass
