import platform
import shlex
from typing import TYPE_CHECKING, assert_never

from rich.console import Console

from stackops.utils.code import run_shell_script
from stackops.utils.installer_utils.installer_main_protocol import InstallerPythonScriptMain
from stackops.utils.installer_utils.linux_package_manager import (
    LinuxDistribution,
    build_metadata_refresh_command,
    build_package_install_command,
    detect_current_linux_distribution,
)
from stackops.utils.meta import print_code
from stackops.utils.schemas.installer.installer_types import InstallerData


def _build_linux_install_script(distribution: LinuxDistribution) -> str:
    match distribution.package_manager:
        case "apk":
            raise NotImplementedError("Oz does not publish an Alpine Linux APK repository or package.")
        case "apt":
            dependency_packages = ("ca-certificates", "wget", "gpg")
            repository_setup = """
sudo install -m 0755 -d /etc/apt/keyrings
wget -qO- https://releases.warp.dev/linux/keys/warp.asc \
    | gpg --dearmor \
    | sudo tee /etc/apt/keyrings/warpdotdev.gpg >/dev/null
echo "deb [signed-by=/etc/apt/keyrings/warpdotdev.gpg] https://releases.warp.dev/linux/deb stable main" \
    | sudo tee /etc/apt/sources.list.d/warpdotdev.list >/dev/null
""".strip()
        case "dnf":
            dependency_packages = ("ca-certificates", "wget", "gnupg2")
            repository_setup = """
sudo rpm --import https://releases.warp.dev/linux/keys/warp.asc
sudo tee /etc/yum.repos.d/warpdotdev.repo >/dev/null <<'EOF'
[warpdotdev]
name=warpdotdev
baseurl=https://releases.warp.dev/linux/rpm/stable
enabled=1
gpgcheck=1
gpgkey=https://releases.warp.dev/linux/keys/warp.asc
EOF
""".strip()
        case "pacman":
            dependency_packages = ("ca-certificates", "wget", "gnupg")
            repository_setup = """
if ! grep -qxF '[warpdotdev]' /etc/pacman.conf; then
    printf '%s\n' '' '[warpdotdev]' 'Server = https://releases.warp.dev/linux/pacman/$repo/$arch' \
        | sudo tee -a /etc/pacman.conf >/dev/null
fi
sudo pacman-key -r linux-maintainers@warp.dev
sudo pacman-key --lsign-key linux-maintainers@warp.dev
""".strip()
        case _:
            assert_never(distribution.package_manager)
    refresh = shlex.join(("sudo", *build_metadata_refresh_command(distribution.package_manager)))
    install_dependencies = shlex.join(
        ("sudo", *build_package_install_command(package_manager=distribution.package_manager, packages=dependency_packages))
    )
    install_oz = shlex.join(("sudo", *build_package_install_command(package_manager=distribution.package_manager, packages=("oz-stable",))))
    return f"""set -euo pipefail
{refresh}
{install_dependencies}
{repository_setup}
{refresh}
{install_oz}
"""


def main(installer_data: InstallerData, version: str | None, update: bool) -> None:
    _ = installer_data, version, update
    if platform.system() != "Linux":
        raise NotImplementedError(f"Oz Linux installer cannot run on {platform.system()}")
    distribution = detect_current_linux_distribution()
    program = _build_linux_install_script(distribution=distribution)
    console = Console()
    console.print(f"Installing Oz on {distribution.distribution_id} with {distribution.package_manager}.")
    print_code(code=program, lexer="shell", desc="Oz installation")
    result = run_shell_script(program, display_script=True, clean_env=False)
    if result.returncode != 0:
        raise RuntimeError(f"Oz installation failed with exit code {result.returncode}")


if __name__ == "__main__":
    if TYPE_CHECKING:
        _main_protocol_check: InstallerPythonScriptMain = main
