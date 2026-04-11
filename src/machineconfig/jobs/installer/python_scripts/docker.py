"""docker installer"""

import platform
from typing import TYPE_CHECKING

from rich import box
from rich.console import Console
from rich.panel import Panel

from machineconfig.jobs.installer.python_scripts.main_protocol import (
    InstallerPythonScriptMain,
)
from machineconfig.utils.code import print_code, run_shell_script
from machineconfig.utils.schemas.installer.installer_types import InstallerData


def _get_linux_install_script() -> str:
    return """
set -euo pipefail

echo "🔍 DETECTING SYSTEM | Identifying OS distribution and version"

get_os_type() {
    if [[ -f "/etc/ubuntu_version" || -f "/etc/lsb-release" ]]; then
        echo "ubuntu"
        return
    fi
    if [[ -f "/etc/debian_version" ]]; then
        echo "debian"
        return
    fi
    echo "unsupported"
}

get_linux_codename() {
    local os_type
    os_type="$(get_os_type)"
    local distro_codename
    distro_codename="$(lsb_release -cs)"
    if [[ "$os_type" == "ubuntu" ]]; then
        case "$distro_codename" in
            wilma)
                echo "noble"
                ;;
            virginia)
                echo "jammy"
                ;;
            *)
                echo "$distro_codename"
                ;;
        esac
        return
    fi
    echo "$distro_codename"
}

OS_TYPE="$(get_os_type)"
if [[ "$OS_TYPE" == "unsupported" ]]; then
    echo "❌ Unsupported Linux distribution. Expected Debian/Ubuntu family."
    exit 1
fi

DISTRO_VERSION="$(get_linux_codename)"

echo "🖥️ Detected OS: $OS_TYPE"
echo "📋 Distribution version: $DISTRO_VERSION"

echo "📥 Installing prerequisites..."
sudo nala update
sudo nala install ca-certificates curl gnupg lsb-release -y

echo "🔐 Adding Docker's official GPG key..."
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL "https://download.docker.com/linux/$OS_TYPE/gpg" | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo "📝 Adding Docker repository to sources list..."
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$OS_TYPE \
  $DISTRO_VERSION stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

echo "📦 INSTALLATION | Installing Docker packages"
sudo nala update
sudo nala install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin -y

echo "⚙️ Enabling Docker system service..."
sudo systemctl enable docker || echo "⚠️ Could not enable Docker service (may be WSL or systemd not available)"

echo "▶️ Starting Docker system service..."
sudo systemctl start docker || echo "⚠️ Could not start Docker service automatically"

echo "👥 Adding current user to docker group..."
sudo groupadd docker 2>/dev/null || echo "ℹ️ Docker group already exists"
sudo usermod -aG docker "$(id -un)" || echo "⚠️ Failed to add user to docker group"

echo "🧪 Testing Docker installation with hello-world..."
sudo docker run hello-world || docker run hello-world || echo "⚠️ Docker hello-world test failed (you may need to re-login or start the Docker daemon manually)"

echo "✅ Docker installation completed"
echo "ℹ️ Log out and back in, or run 'newgrp docker', before using Docker without sudo."
"""


def _get_darwin_install_script() -> str:
    return """
set -euo pipefail

echo "🍎 DETECTING SYSTEM | Preparing macOS Docker installation"

if ! command -v brew >/dev/null 2>&1; then
    echo "❌ Homebrew is required to install Docker on macOS."
    exit 1
fi

echo "🔄 Updating Homebrew..."
brew update

echo "📥 Installing Docker CLI packages..."
brew install docker docker-buildx docker-compose

echo "🖥️ Installing Docker Desktop..."
brew install --cask docker

echo "🚀 Launching Docker Desktop..."
open -a Docker || echo "⚠️ Could not launch Docker Desktop automatically"

echo "🧪 Testing Docker installation with hello-world..."
docker run hello-world || echo "⚠️ Docker hello-world test failed (Docker Desktop may still be starting; open Docker.app and retry)"

echo "✅ Docker installation completed"
echo "ℹ️ If Docker Desktop prompts for permissions on first launch, approve them and rerun the hello-world test."
"""


def main(installer_data: InstallerData, version: str | None, update: bool) -> None:
    console = Console()
    _ = installer_data, update
    console.print(
        Panel.fit(
            "\n".join(
                [
                    f"💻 Platform: {platform.system()}",
                    f"🔄 Version: {'latest' if version is None else version}",
                ]
            ),
            title="🐳 Docker Installer",
            border_style="blue",
            box=box.ROUNDED,
        )
    )

    _ = version
    match platform.system():
        case "Linux":
            console.print("🐧 Installing Docker on Linux with Docker's official apt repository...", style="bold")
            program = _get_linux_install_script()
        case "Darwin":
            console.print("🍎 Installing Docker on macOS with Homebrew and Docker Desktop...", style="bold")
            program = _get_darwin_install_script()
        case "Windows":
            error_msg = "Docker installation is not supported on Windows through this installer"
            console.print(
                Panel.fit(
                    "\n".join([error_msg, "💡 Use Docker Desktop directly or install through a Windows-specific installer entry."]),
                    title="❌ Error",
                    subtitle="⚠️ Unsupported platform",
                    border_style="red",
                    box=box.ROUNDED,
                )
            )
            raise NotImplementedError(error_msg)
        case _:
            error_msg = f"Unsupported platform: {platform.system()}"
            console.print(
                Panel.fit(
                    error_msg,
                    title="❌ Error",
                    subtitle="⚠️ Unsupported platform",
                    border_style="red",
                    box=box.ROUNDED,
                )
            )
            raise NotImplementedError(error_msg)

    print_code(code=program, lexer="shell", desc="Installation Script Preview")
    result = run_shell_script(program, display_script=True, clean_env=False)
    if result.returncode != 0:
        console.print(f"❌ Docker installation failed with exit code {result.returncode}", style="bold red")
        raise RuntimeError(f"Docker installation failed with exit code {result.returncode}")
    console.print("✅ Docker installation completed successfully", style="bold green")


if __name__ == "__main__":
    if TYPE_CHECKING:
        _main_protocol_check: InstallerPythonScriptMain = main
    pass