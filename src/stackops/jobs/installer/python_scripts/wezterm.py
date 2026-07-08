"""wezterm installer"""

import platform
import subprocess
from typing import TYPE_CHECKING, assert_never

from rich.console import Console
from rich.panel import Panel

from stackops.utils.installer_utils.installer_main_protocol import InstallerPythonScriptMain
from stackops.utils.installer_utils.linux_package_manager import LinuxDistribution, detect_current_linux_distribution
from stackops.utils.schemas.installer.installer_types import InstallerData

console = Console()


def _build_linux_install_script(distribution: LinuxDistribution) -> str:
    match distribution.package_manager:
        case "apt":
            repository_setup = """
echo "📥 Installing APT repository prerequisites..."
sudo apt-get update
sudo apt-get install -y curl gpg

echo "🔐 Adding WezTerm's signing key..."
curl -fsSL https://apt.fury.io/wez/gpg.key | sudo gpg --yes --dearmor -o /usr/share/keyrings/wezterm-fury.gpg
sudo chmod 644 /usr/share/keyrings/wezterm-fury.gpg

echo "📝 Adding WezTerm's APT repository..."
echo 'deb [signed-by=/usr/share/keyrings/wezterm-fury.gpg] https://apt.fury.io/wez/ * *' | sudo tee /etc/apt/sources.list.d/wezterm.list > /dev/null
sudo apt-get update
"""
            install_command = "sudo apt-get install -y wezterm"
        case "dnf":
            repository_setup = """
echo "📥 Installing COPR repository support..."
sudo dnf install -y dnf-plugins-core

echo "📝 Enabling WezTerm's official COPR project..."
sudo dnf copr enable -y wezfurlong/wezterm-nightly
"""
            install_command = "sudo dnf install -y wezterm"
        case "pacman":
            repository_setup = """
echo "📦 Using Arch Linux's official repositories..."
""".strip()
            install_command = "sudo pacman -S --needed --noconfirm wezterm"
        case _:
            assert_never(distribution.package_manager)

    return f"""#!/usr/bin/env bash
set -euo pipefail

echo "🖥️ Installing WezTerm on {distribution.distribution_id} with {distribution.package_manager}"
{repository_setup}

echo "📦 Installing WezTerm..."
{install_command}

echo "✅ WezTerm installation completed"
"""


def main(installer_data: InstallerData, version: str | None, update: bool) -> None:
    _ = installer_data, update
    system = platform.system()
    console.print(
        Panel.fit(
            "\n".join(
                ["🖥️  WEZTERM INSTALLER | Modern, GPU-accelerated terminal emulator", f"💻 Platform: {system}", f"🔄 Version: {version or 'latest'}"]
            ),
            title="WezTerm Setup",
            border_style="magenta",
            padding=(1, 2),
        )
    )

    match system:
        case "Windows":
            program = """winget install --no-upgrade --name "WezTerm" --Id "wez.wezterm" --source winget --accept-package-agreements --accept-source-agreements
"""
        case "Linux":
            distribution = detect_current_linux_distribution()
            console.print(
                Panel.fit(
                    f"🐧 Installing WezTerm on {distribution.distribution_id} with {distribution.package_manager}...",
                    title="Platform Setup",
                    border_style="cyan",
                )
            )
            program = _build_linux_install_script(distribution)
        case "Darwin":
            console.print(Panel.fit("🍎 Installing WezTerm on macOS...", title="Platform Setup", border_style="cyan"))
            program = "brew install --cask wezterm"
        case _:
            error_msg = f"Unsupported platform: {system}"
            console.print(Panel.fit(f"❌ ERROR | {error_msg}", title="Unsupported Platform", border_style="red"))
            raise NotImplementedError(error_msg)

    if system == "Windows":
        subprocess.run(program, shell=True, text=True, check=True)
    else:
        subprocess.run(["bash", "-c", program], text=True, check=True)
    console.print("[green]✅ WezTerm installation completed successfully[/green]")


if __name__ == "__main__":
    if TYPE_CHECKING:
        _main_protocol_check: InstallerPythonScriptMain = main
    pass
