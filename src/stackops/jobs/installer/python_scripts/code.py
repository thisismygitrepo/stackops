"""vs code installer as per https://code.visualstudio.com/docs/setup/linux"""

import platform
from typing import TYPE_CHECKING, assert_never

from rich import box
from rich.console import Console
from rich.panel import Panel

from stackops.utils.code import run_shell_script
from stackops.utils.installer_utils.installer_main_protocol import InstallerPythonScriptMain
from stackops.utils.installer_utils.linux_package_manager import LinuxDistribution, detect_current_linux_distribution
from stackops.utils.schemas.installer.installer_types import InstallerData


def _build_linux_install_script(distribution: LinuxDistribution) -> str:
    match distribution.package_manager:
        case "apt":
            repository_setup = """
echo "📥 Installing APT repository prerequisites..."
sudo apt-get update
sudo apt-get install -y wget gpg

echo "🔐 Adding Microsoft's signing key..."
wget -qO- https://packages.microsoft.com/keys/microsoft.asc | sudo gpg --yes --dearmor -o /usr/share/keyrings/microsoft.gpg

echo "📝 Adding Microsoft's VS Code repository..."
sudo tee /etc/apt/sources.list.d/vscode.sources > /dev/null <<'EOF'
Types: deb
URIs: https://packages.microsoft.com/repos/code
Suites: stable
Components: main
Architectures: amd64,arm64,armhf
Signed-By: /usr/share/keyrings/microsoft.gpg
EOF
sudo apt-get update
"""
            install_command = "sudo apt-get install -y code"
        case "dnf":
            repository_setup = """
echo "🔐 Importing Microsoft's signing key..."
sudo rpm --import https://packages.microsoft.com/keys/microsoft.asc

echo "📝 Adding Microsoft's VS Code repository..."
sudo tee /etc/yum.repos.d/vscode.repo > /dev/null <<'EOF'
[code]
name=Visual Studio Code
baseurl=https://packages.microsoft.com/yumrepos/vscode
enabled=1
autorefresh=1
type=rpm-md
gpgcheck=1
gpgkey=https://packages.microsoft.com/keys/microsoft.asc
EOF
sudo dnf makecache --refresh
"""
            install_command = "sudo dnf install -y code"
        case _:
            assert_never(distribution.package_manager)

    return f"""#!/usr/bin/env bash
set -euo pipefail

echo "💻 Installing VS Code on {distribution.distribution_id} with {distribution.package_manager}"
{repository_setup}

echo "📦 Installing Visual Studio Code..."
{install_command}

echo "✅ Visual Studio Code installation completed"
"""


def main(installer_data: InstallerData, version: str | None, update: bool) -> None:
    console = Console()
    _ = installer_data, update
    system = platform.system()
    console.print(
        Panel.fit(
            "\n".join([f"🖥️  Platform: {system}", f"🔄 Version: {'latest' if version is None else version}"]),
            title="💻 VS Code Installer",
            border_style="blue",
            box=box.ROUNDED,
        )
    )

    match system:
        case "Linux":
            distribution = detect_current_linux_distribution()
            console.print(f"🐧 Installing VS Code on {distribution.distribution_id} with Microsoft's official repository...", style="bold")
            install_script = _build_linux_install_script(distribution)
        case "Darwin":
            console.print("🍎 Installing VS Code on macOS using Homebrew...", style="bold")
            install_script = "brew install --cask visual-studio-code"
        case "Windows":
            console.print("🪟 Installing VS Code on Windows using winget...", style="bold")
            install_script = """
winget install --no-upgrade --name "Microsoft Visual Studio Code" --Id "Microsoft.VisualStudioCode" --source winget --scope user --accept-package-agreements --accept-source-agreements
"""
        case _:
            error_msg = f"Unsupported platform: {system}"
            console.print(Panel.fit(error_msg, title="❌ Error", subtitle="⚠️ Unsupported platform", border_style="red", box=box.ROUNDED))
            raise NotImplementedError(error_msg)

    result = run_shell_script(install_script, display_script=True, clean_env=False)
    if result.returncode != 0:
        raise RuntimeError(f"VS Code installation failed with exit code {result.returncode}")


if __name__ == "__main__":
    if TYPE_CHECKING:
        _main_protocol_check: InstallerPythonScriptMain = main
    pass
