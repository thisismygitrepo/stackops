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


def _get_linux_install_script(distribution: LinuxDistribution) -> str:
    match (distribution.distribution_id, distribution.package_manager):
        case ("alpine", "apk"):
            repository_setup = """
echo "📦 Using Alpine Linux's official repositories..."
""".strip()
            install_command = "sudo apk add --no-cache"
            package_names = "docker docker-cli-compose"
        case (("ubuntu" | "debian") as distribution_id, "apt"):
            match distribution_id:
                case "ubuntu":
                    suite_expression = "${UBUNTU_CODENAME:-$VERSION_CODENAME}"
                case "debian":
                    suite_expression = "$VERSION_CODENAME"
            repository_url = f"https://download.docker.com/linux/{distribution_id}"
            repository_setup = f"""
echo "📥 Installing APT repository prerequisites..."
sudo apt-get update
sudo apt-get install -y ca-certificates curl

echo "🔐 Adding Docker's official signing key..."
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL "{repository_url}/gpg" -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

echo "📝 Adding Docker's official {distribution_id} repository..."
sudo tee /etc/apt/sources.list.d/docker.sources > /dev/null <<EOF
Types: deb
URIs: {repository_url}
Suites: $(. /etc/os-release && echo "{suite_expression}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
sudo apt-get update
"""
            install_command = "sudo apt-get install -y"
            package_names = "docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin"
        case (("rhel" | "centos" | "ol") as distribution_id, "dnf"):
            repository_distribution_id = "rhel" if distribution_id == "ol" else distribution_id
            repository_url = f"https://download.docker.com/linux/{repository_distribution_id}/docker-ce.repo"
            repository_setup = f"""
echo "📥 Installing DNF repository prerequisites..."
sudo dnf -y install dnf-plugins-core

echo "📝 Adding Docker's official {repository_distribution_id} repository for {distribution_id}..."
sudo dnf config-manager --add-repo "{repository_url}"
"""
            install_command = "sudo dnf install -y"
            package_names = "docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin"
        case ("fedora", "dnf"):
            repository_setup = """
echo "📝 Adding Docker's official fedora repository..."
sudo dnf config-manager addrepo --from-repofile "https://download.docker.com/linux/fedora/docker-ce.repo"
"""
            install_command = "sudo dnf install -y"
            package_names = "docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin"
        case ("arch", "pacman"):
            repository_setup = """
echo "📦 Using Arch Linux's official repositories..."
""".strip()
            install_command = "sudo pacman -S --needed --noconfirm"
            package_names = "docker docker-buildx docker-compose"
        case ("alpine" | "arch" | "ubuntu" | "debian" | "rhel" | "fedora" | "centos" | "ol", _):
            raise ValueError(
                f"Invalid package-manager metadata for Linux distribution '{distribution.distribution_id}': manager={distribution.package_manager}"
            )
        case (unsupported_distribution_id, _):
            raise NotImplementedError(
                "Docker Engine's official repositories do not support Linux distribution "
                f"'{unsupported_distribution_id}'. Supported distributions: alpine, arch, ubuntu, debian, rhel, fedora, centos, ol."
            )

    match distribution.package_manager:
        case "apk":
            service_setup = """sudo rc-update add docker default
sudo rc-service docker start"""
            add_user_to_group = 'sudo addgroup "$(id -un)" docker'
        case "apt" | "dnf" | "pacman":
            service_setup = "sudo systemctl enable --now docker"
            add_user_to_group = 'sudo usermod -aG docker "$(id -un)"'

    return f"""
set -euo pipefail

echo "🐧 Installing Docker Engine for {distribution.distribution_id} with {distribution.package_manager}"
{repository_setup}

echo "📦 INSTALLATION | Installing Docker packages"
{install_command} {package_names}

echo "⚙️ Enabling and starting Docker system service..."
{service_setup}

echo "👥 Adding current user to docker group..."
{add_user_to_group}

echo "🧪 Testing Docker installation with hello-world..."
sudo docker run hello-world

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
brew install colima
# colima start

echo "✅ Docker installation completed"
echo "ℹ️ This installs the Docker CLI only. You still need a reachable Docker daemon, such as a remote host or a separate local runtime."
"""


def main(installer_data: InstallerData, version: str | None, update: bool) -> None:
    console = Console()
    _ = installer_data, update
    console.print(
        Panel.fit(
            "\n".join([f"💻 Platform: {platform.system()}", f"🔄 Version: {'latest' if version is None else version}"]),
            title="🐳 Docker Installer",
            border_style="blue",
            box=box.ROUNDED,
        )
    )

    match platform.system():
        case "Linux":
            distribution = detect_current_linux_distribution()
            console.print(f"🐧 Installing Docker on {distribution.distribution_id} with Docker's official repository...", style="bold")
            program = _get_linux_install_script(distribution=distribution)
        case "Darwin":
            console.print("🍎 Installing Docker CLI on macOS with Homebrew...", style="bold")
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
            console.print(Panel.fit(error_msg, title="❌ Error", subtitle="⚠️ Unsupported platform", border_style="red", box=box.ROUNDED))
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
