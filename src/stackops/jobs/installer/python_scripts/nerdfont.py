"""Nerd Fonts installer - Cross-platform font installation"""

import os
import platform
import subprocess
from typing import TYPE_CHECKING

from rich import box
from rich.console import Console
from rich.panel import Panel

import stackops.jobs.installer.linux_scripts as linux_scripts
import stackops.jobs.installer.macos_scripts as macos_scripts
from stackops.jobs.installer.python_scripts.main_protocol import (
    InstallerPythonScriptMain,
)
from stackops.utils.path_reference import get_path_reference_path
from stackops.utils.schemas.installer.installer_types import InstallerData


def main(installer_data: InstallerData, version: str | None, update: bool) -> None:
    """Main entry point for Nerd Fonts installation.

    Args:
        installer_data: Installation configuration data
        version: Specific version to install (None for latest)
    """
    console = Console()
    _ = installer_data, update
    console.print(
        Panel.fit(
            "\n".join([f"💻 Platform: {platform.system()}", f"🔄 Version: {'latest' if version is None else version}"]),
            title="🔤 Nerd Fonts Installer",
            border_style="blue",
            box=box.ROUNDED,
        )
    )

    current_platform = platform.system()

    if current_platform == "Windows":
        console.print("🪟 Installing Nerd Fonts on Windows...", style="bold")
        from stackops.jobs.installer.python_scripts.nerfont_windows_helper import install_nerd_fonts

        try:
            install_nerd_fonts()
            console.print(
                Panel.fit(
                    "\n".join(["💡 Restart terminal applications to see the new fonts."]),
                    title="✅ Nerd Fonts Installed",
                    border_style="green",
                    box=box.ROUNDED,
                )
            )
        except Exception as e:  # noqa: BLE001
            error_msg = f"Windows Nerd Fonts installation failed: {e}"
            console.print(
                Panel.fit(
                    "\n".join(
                        [
                            error_msg,
                            "💡 Try running as administrator or install manually from https://www.nerdfonts.com",
                        ]
                    ),
                    title="❌ Error",
                    subtitle="⚠️ Installation issue",
                    border_style="red",
                    box=box.ROUNDED,
                )
            )
            raise RuntimeError(error_msg) from e

    else:
        if current_platform == "Linux":
            script_module = linux_scripts
            path_reference = linux_scripts.NERDFONT_PATH_REFERENCE
            platform_label = "Linux"
        elif current_platform == "Darwin":
            script_module = macos_scripts
            path_reference = macos_scripts.NERDFONT_PATH_REFERENCE
            platform_label = "macOS"
        else:
            error_msg = f"Unsupported platform: {current_platform}"
            console.print(
                Panel.fit(
                    "\n".join([error_msg, "💡 Supported platforms are Windows, Linux, and macOS (Darwin)"]),
                    title="❌ Error",
                    subtitle="⚠️ Unsupported platform",
                    border_style="red",
                    box=box.ROUNDED,
                )
            )
            raise NotImplementedError(error_msg)

        console.print(f"Installing Nerd Fonts on {platform_label} using installation script...", style="bold")

        script_path = get_path_reference_path(
            module=script_module,
            path_reference=path_reference,
        )

        console.print(
            Panel.fit(
                "\n".join(
                    [
                        "🎨 Programming fonts patched with icons",
                        "🔣 Includes icons from popular sets (FontAwesome, Devicons, etc.)",
                        "🖥️  Perfect for terminals and coding environments",
                        "🧰 Works with many terminal applications and editors",
                    ]
                ),
                title="ℹ️  Nerd Fonts Features",
                border_style="magenta",
                box=box.ROUNDED,
            )
        )

        console.print("🔄 EXECUTING | Running Nerd Fonts installation...", style="bold yellow")
        try:
            env = os.environ.copy()
            if version is not None:
                env["NERDFONT_VERSION"] = version
            subprocess.run(["bash", str(script_path)], text=True, check=True, env=env)
            console.print("✅ Nerd Fonts installation completed successfully", style="bold green")
        except subprocess.CalledProcessError as e:
            console.print(f"❌ Installation failed with exit code {e.returncode}", style="bold red")
            raise


if __name__ == "__main__":
    if TYPE_CHECKING:
        _main_protocol_check: InstallerPythonScriptMain = main
    pass
