"""A text expander is a program that detects when you type a specific keyword and replaces it with something else

https://github.com/espanso/espanso
"""

import subprocess
from typing import TYPE_CHECKING
from rich import box
from rich.console import Console
from rich.panel import Panel
from machineconfig.jobs.installer.python_scripts.main_protocol import (
    InstallerPythonScriptMain,
    
)
from machineconfig.utils.schemas.installer.installer_types import InstallerData


def main(installer_data: InstallerData, version: str | None, update: bool) -> None:
    console = Console()
    _ = installer_data, update
    console.print(
        Panel.fit(
            "\n".join(
                [
                    f"🔄 Version: {'latest' if version is None else version}",
                    "🔗 Source: https://github.com/espanso/espanso",
                ]
            ),
            title="⚡ Espanso Installer",
            border_style="yellow",
            box=box.ROUNDED,
        )
    )

    _ = version
    import platform

    installer_data["repoURL"] = "https://github.com/espanso/espanso"
    if platform.system() == "Windows":
        console.print("🪟 Installing Espanso on Windows...", style="bold")
    elif platform.system() in ["Linux", "Darwin"]:
        if platform.system() == "Linux":
            import os

            env = os.environ["XDG_SESSION_TYPE"]
            if env == "wayland":
                console.print(
                    Panel.fit(
                        "\n".join(["Wayland detected", "📦 Using Wayland-specific package"]),
                        title="🖥️  Display Server",
                        border_style="cyan",
                        box=box.ROUNDED,
                    )
                )
                installer_data["fileNamePattern"]["amd64"]["linux"] = "espanso-debian-wayland-amd64.deb"
            else:
                console.print(
                    Panel.fit(
                        "\n".join(["X11 detected", "📦 Using X11-specific package"]),
                        title="🖥️  Display Server",
                        border_style="cyan",
                        box=box.ROUNDED,
                    )
                )
                installer_data["fileNamePattern"]["amd64"]["linux"] = "espanso-debian-x11-amd64.deb"
        else:  # Darwin/macOS
            console.print("🍎 Installing Espanso on macOS...", style="bold")
            installer_data["fileNamePattern"]["amd64"]["macos"] = "Espanso.dmg"
    else:
        error_msg = f"Unsupported platform: {platform.system()}"
        console.print(
            Panel.fit(
                "\n".join([error_msg]),
                title="❌ Error",
                subtitle="⚠️ Unsupported platform",
                border_style="red",
                box=box.ROUNDED,
            )
        )
        raise NotImplementedError(error_msg)

    console.print("🚀 Installing Espanso using installer...", style="bold yellow")
    from machineconfig.utils.installer_utils.installer_class import Installer

    installer = Installer(installer_data)
    installer.install(version=None)

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
