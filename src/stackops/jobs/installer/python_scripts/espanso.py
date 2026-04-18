"""A text expander is a program that detects when you type a specific keyword and replaces it with something else

https://github.com/espanso/espanso
"""

import os
import subprocess
from typing import TYPE_CHECKING

from rich import box
from rich.console import Console
from rich.panel import Panel

from stackops.jobs.installer.python_scripts.main_protocol import (
    InstallerPythonScriptMain,
)
from stackops.utils.installer_utils.installer_class import Installer
from stackops.utils.schemas.installer.installer_types import (
    CPU_ARCHITECTURES,
    OPERATING_SYSTEMS,
    InstallerData,
    get_normalized_arch,
    get_os_name,
)


ESPANSO_REPO_URL = "https://github.com/espanso/espanso"
ESPANSO_WINDOWS_PORTABLE_ASSET = "Espanso-Win-Portable-x86_64.zip"
ESPANSO_MACOS_UNIVERSAL_ASSET = "Espanso-Mac-Universal.zip"


def _empty_file_name_pattern() -> dict[CPU_ARCHITECTURES, dict[OPERATING_SYSTEMS, str | None]]:
    return {
        "amd64": {
            "linux": None,
            "windows": None,
            "darwin": None,
        },
        "arm64": {
            "linux": None,
            "windows": None,
            "darwin": None,
        },
    }


def _resolve_linux_asset_name(current_arch: CPU_ARCHITECTURES, xdg_session_type: str) -> str:
    if current_arch != "amd64":
        raise NotImplementedError("Espanso only publishes Linux packages for amd64.")
    if xdg_session_type == "wayland":
        return "espanso-debian-wayland-amd64.deb"
    return "espanso-debian-x11-amd64.deb"


def _build_espanso_installer_data(
    base_installer_data: InstallerData,
    os_name: OPERATING_SYSTEMS,
    arch: CPU_ARCHITECTURES,
    xdg_session_type: str | None,
) -> InstallerData:
    file_name_pattern = _empty_file_name_pattern()
    match os_name:
        case "windows":
            if arch != "amd64":
                raise NotImplementedError("Espanso only publishes Windows portable builds for amd64.")
            file_name_pattern["amd64"]["windows"] = ESPANSO_WINDOWS_PORTABLE_ASSET
        case "linux":
            if xdg_session_type is None:
                raise RuntimeError("XDG_SESSION_TYPE must be set for Linux Espanso installations.")
            file_name_pattern[arch]["linux"] = _resolve_linux_asset_name(
                current_arch=arch,
                xdg_session_type=xdg_session_type,
            )
        case "darwin":
            file_name_pattern["amd64"]["darwin"] = ESPANSO_MACOS_UNIVERSAL_ASSET
            file_name_pattern["arm64"]["darwin"] = ESPANSO_MACOS_UNIVERSAL_ASSET
    return InstallerData(
        appName=base_installer_data["appName"],
        license=base_installer_data["license"],
        doc=base_installer_data["doc"],
        repoURL=ESPANSO_REPO_URL,
        fileNamePattern=file_name_pattern,
    )


def main(installer_data: InstallerData, version: str | None, update: bool) -> None:
    console = Console()
    _ = update
    os_name = get_os_name()
    arch = get_normalized_arch()
    xdg_session_type = os.environ["XDG_SESSION_TYPE"] if os_name == "linux" else None
    resolved_installer_data = _build_espanso_installer_data(
        base_installer_data=installer_data,
        os_name=os_name,
        arch=arch,
        xdg_session_type=xdg_session_type,
    )
    console.print(
        Panel.fit(
            "\n".join(
                [
                    f"🔄 Version: {'latest' if version is None else version}",
                    f"🔗 Source: {ESPANSO_REPO_URL}",
                ]
            ),
            title="⚡ Espanso Installer",
            border_style="yellow",
            box=box.ROUNDED,
        )
    )

    if os_name == "windows":
        console.print("🪟 Installing Espanso on Windows...", style="bold")
    elif os_name == "linux":
        if xdg_session_type == "wayland":
            console.print(
                Panel.fit(
                    "\n".join(["Wayland detected", "📦 Using Wayland-specific package"]),
                    title="🖥️  Display Server",
                    border_style="cyan",
                    box=box.ROUNDED,
                )
            )
        else:
            console.print(
                Panel.fit(
                    "\n".join(["X11 detected", "📦 Using X11-specific package"]),
                    title="🖥️  Display Server",
                    border_style="cyan",
                    box=box.ROUNDED,
                )
            )
    else:
        console.print("🍎 Installing Espanso on macOS...", style="bold")

    console.print("🚀 Installing Espanso using installer...", style="bold yellow")
    installer = Installer(resolved_installer_data)
    installer.install(version=version)

    config = """
espanso service register
espanso start
espanso install actually-all-emojis
    """

    console.print(
        Panel.fit(
            "\n".join(
                [
                    "📋 Post-installation steps:",
                    "1️⃣  Register Espanso as a service",
                    "2️⃣  Start the Espanso service",
                    "3️⃣  Install the emoji package",
                ]
            ),
            title="✅ Espanso Installation Completed",
            border_style="green",
            box=box.ROUNDED,
        )
    )

    console.print("🔄 EXECUTING | Running Espanso configuration...", style="bold yellow")
    try:
        subprocess.run(config, shell=True, text=True, check=True)
        console.print("✅ Espanso configuration completed successfully", style="bold green")
    except subprocess.CalledProcessError as e:
        console.print(f"❌ Configuration failed with exit code {e.returncode}", style="bold red")
        raise


if __name__ == "__main__":
    if TYPE_CHECKING:
        _main_protocol_check: InstallerPythonScriptMain = main
