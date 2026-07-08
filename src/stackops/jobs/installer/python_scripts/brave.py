"""brave installer"""

import platform
from typing import TYPE_CHECKING

from rich import box
from rich.console import Console
from rich.panel import Panel

from stackops.utils.code import run_shell_script
from stackops.utils.installer_utils.installer_main_protocol import InstallerPythonScriptMain
from stackops.utils.installer_utils.linux_package_manager import LinuxDistribution, detect_current_linux_distribution
from stackops.utils.meta import print_code
from stackops.utils.schemas.installer.installer_types import InstallerData


def _build_linux_install_script(distribution: LinuxDistribution) -> str:
    match (distribution.distribution_id, distribution.package_manager):
        case (_, "apt"):
            repository_setup = """
echo "📥 Installing APT repository prerequisites..."
sudo apt-get update
sudo apt-get install -y curl

echo "🔐 Adding Brave's official signing key and repository..."
sudo curl -fsSLo /usr/share/keyrings/brave-browser-archive-keyring.gpg https://brave-browser-apt-release.s3.brave.com/brave-browser-archive-keyring.gpg
sudo curl -fsSLo /etc/apt/sources.list.d/brave-browser-release.sources https://brave-browser-apt-release.s3.brave.com/brave-browser.sources
sudo apt-get update
"""
            install_command = "sudo apt-get install -y brave-browser"
        case ("fedora", "dnf"):
            repository_setup = """
echo "📥 Installing DNF repository prerequisites..."
sudo dnf install -y dnf-plugins-core

echo "📝 Adding Brave's official Fedora repository..."
sudo dnf config-manager addrepo --from-repofile=https://brave-browser-rpm-release.s3.brave.com/brave-browser.repo
"""
            install_command = "sudo dnf install -y brave-browser"
        case ("rhel" | "rocky" | "centos", "dnf"):
            repository_setup = """
echo "📥 Installing DNF repository prerequisites..."
sudo dnf install -y dnf-plugins-core

echo "📝 Adding Brave's official RPM repository..."
sudo dnf config-manager --add-repo https://brave-browser-rpm-release.s3.brave.com/brave-browser.repo
"""
            install_command = "sudo dnf install -y brave-browser"
        case (unsupported_distribution_id, "dnf"):
            raise NotImplementedError(
                "Brave's official RPM instructions do not support Linux distribution "
                f"'{unsupported_distribution_id}'. Supported RPM distributions: fedora, rhel, rocky, centos."
            )

    return f"""#!/usr/bin/env bash
set -euo pipefail

echo "🦁 Installing Brave on {distribution.distribution_id} with {distribution.package_manager}"
{repository_setup}

echo "📦 Installing Brave Browser..."
{install_command}

echo "✅ Brave Browser installation completed"
"""


def main(installer_data: InstallerData, version: str | None, update: bool) -> None:
    console = Console()
    _ = installer_data, update
    system = platform.system()
    console.print(
        Panel.fit(
            "\n".join([f"💻 Platform: {system}", f"🔄 Version: {'latest' if version is None else version}"]),
            title="🦁 Brave Browser Installer",
            border_style="orange1",
            box=box.ROUNDED,
        )
    )

    match system:
        case "Windows":
            console.print("🪟 Installing Brave Browser on Windows using winget...", style="bold")
            program = """
winget install --no-upgrade --name "Brave" --Id "Brave.Brave" --source winget --scope user --accept-package-agreements --accept-source-agreements
"""
        case "Linux":
            distribution = detect_current_linux_distribution()
            console.print(f"🐧 Installing Brave Browser on {distribution.distribution_id} with its official repository...", style="bold")
            program = _build_linux_install_script(distribution)
        case "Darwin":
            console.print("🍎 Installing Brave Browser on macOS...", style="bold")
            program = "brew install --cask brave-browser"
        case _:
            error_msg = f"Unsupported platform: {system}"
            console.print(Panel.fit(error_msg, title="❌ Error", subtitle="⚠️ Unsupported platform", border_style="red", box=box.ROUNDED))
            raise NotImplementedError(error_msg)

    print_code(code=program, lexer="shell", desc="Installation Script Preview")
    result = run_shell_script(program, display_script=True, clean_env=False)
    if result.returncode != 0:
        raise RuntimeError(f"Brave Browser installation failed with exit code {result.returncode}")
    console.print("✅ Installation completed successfully!", style="bold green")


if __name__ == "__main__":
    if TYPE_CHECKING:
        _main_protocol_check: InstallerPythonScriptMain = main
    pass
