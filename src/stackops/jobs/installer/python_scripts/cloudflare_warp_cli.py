import platform
import subprocess
from typing import TYPE_CHECKING

from stackops.utils.installer_utils.installer_main_protocol import InstallerPythonScriptMain
from stackops.utils.installer_utils.linux_package_manager import LinuxDistribution, detect_current_linux_distribution
from stackops.utils.schemas.installer.installer_types import InstallerData


def _build_linux_install_script(distribution: LinuxDistribution) -> str:
    match (distribution.distribution_id, distribution.package_manager):
        case ("alpine", "apk"):
            raise NotImplementedError("Cloudflare WARP does not publish an Alpine Linux APK repository or package.")
        case ("ubuntu" | "debian", "apt"):
            repository_setup = """
echo "📥 Installing APT repository prerequisites..."
sudo apt-get update
sudo apt-get install -y curl gpg lsb-release

echo "🔐 Adding Cloudflare's current signing key..."
curl -fsSL https://pkg.cloudflareclient.com/pubkey.gpg | sudo gpg --yes --dearmor --output /usr/share/keyrings/cloudflare-warp-archive-keyring.gpg

echo "📝 Adding Cloudflare's APT repository..."
echo "deb [signed-by=/usr/share/keyrings/cloudflare-warp-archive-keyring.gpg] https://pkg.cloudflareclient.com/ $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/cloudflare-client.list > /dev/null
sudo apt-get update
"""
            install_command = "sudo apt-get install -y cloudflare-warp"
        case ("fedora", "dnf"):
            repository_setup = """
echo "📥 Installing RPM repository prerequisites..."
sudo dnf install -y curl

echo "🔐 Importing Cloudflare's current signing key..."
sudo rpm --import https://pkg.cloudflareclient.com/pubkey.gpg

echo "📝 Adding Cloudflare's RPM repository..."
sudo curl -fsSLo /etc/yum.repos.d/cloudflare-warp.repo https://pkg.cloudflareclient.com/cloudflare-warp-ascii.repo
sudo dnf makecache --refresh
"""
            install_command = "sudo dnf install -y cloudflare-warp"
        case ("rhel" | "centos", "dnf"):
            raise NotImplementedError("Cloudflare WARP on RHEL and CentOS requires an explicit, version-specific EPEL setup.")
        case (unsupported_distribution_id, _):
            raise NotImplementedError(
                "Cloudflare's package repository does not support Linux distribution "
                f"'{unsupported_distribution_id}'. Supported without extra repositories: ubuntu, debian, fedora."
            )

    return f"""#!/usr/bin/env bash
set -euo pipefail

echo "🔒 Installing Cloudflare WARP on {distribution.distribution_id} with {distribution.package_manager}"
{repository_setup}

echo "📦 Installing Cloudflare WARP..."
{install_command}

echo "📡 Registering the WARP client..."
warp-cli registration new

echo "✅ Cloudflare WARP installation completed"
"""


def main(installer_data: InstallerData, version: str | None, update: bool) -> str:
    _ = installer_data, version, update
    system = platform.system()
    match system:
        case "Windows":
            raise NotImplementedError("Installer is not yet implemented for Windows.")
        case "Linux":
            distribution = detect_current_linux_distribution()
            program = _build_linux_install_script(distribution)
        case "Darwin":
            program = "brew install --cask cloudflare-warp"
        case _:
            raise NotImplementedError(f"Unsupported platform: {system}")
    subprocess.run(["bash", "-c", program], text=True, check=True)
    return f"Cloudflare WARP CLI installed successfully on {system}."


if __name__ == "__main__":
    if TYPE_CHECKING:
        _main_protocol_check: InstallerPythonScriptMain = main
