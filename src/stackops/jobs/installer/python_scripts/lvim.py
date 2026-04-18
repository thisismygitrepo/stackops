"""lvim"""

from rich import box
from rich.console import Console
from rich.panel import Panel
import subprocess
import platform
from typing import TYPE_CHECKING
from stackops.jobs.installer.python_scripts.main_protocol import (
    InstallerPythonScriptMain,
    
)
from stackops.utils.schemas.installer.installer_types import InstallerData


# as per https://www.lunarvim.org/docs/installation


def main(installer_data: InstallerData, version: str | None, update: bool) -> None:
    console = Console()
    _ = installer_data, update
    console.print(
        Panel.fit(
            "\n".join(
                [
                    f"🔄 Version: {'latest' if version is None else version}",
                    "📚 Branch: release-1.4/neovim-0.9",
                ]
            ),
            title="🌙 LunarVim Installer",
            border_style="purple",
            box=box.ROUNDED,
        )
    )

    _ = version
    if platform.system() == "Windows":
        console.print("🪟 Installing LunarVim on Windows...", style="bold")
        program = """

pwsh -c "`$LV_BRANCH='release-1.4/neovim-0.9'; iwr https://raw.githubusercontent.com/LunarVim/LunarVim/release-1.4/neovim-0.9/utils/installer/install.ps1 -UseBasicParsing | iex"

"""
    elif platform.system() in ["Linux", "Darwin"]:
        system_name = "Linux" if platform.system() == "Linux" else "macOS"
        console.print(f"🐧 Installing LunarVim on {system_name}...", style="bold")
        program = """

LV_BRANCH='release-1.4/neovim-0.9' bash <(curl -s https://raw.githubusercontent.com/LunarVim/LunarVim/release-1.4/neovim-0.9/utils/installer/install.sh)

"""
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

    console.print(
        Panel.fit(
            "\n".join(
                [
                    "📝 IDE-like experience for Neovim",
                    "🔌 Built-in plugin management",
                    "🛠️  LSP configuration out of the box",
                    "🔍 Powerful fuzzy finding",
                    "⚙️  Simple and unified configuration",
                    "⚠️  Installer will prompt for user input during installation.",
                ]
            ),
            title="ℹ️  LunarVim Features",
            border_style="magenta",
            box=box.ROUNDED,
        )
    )

    console.print("🔄 EXECUTING | Running LunarVim installation...", style="bold yellow")
    try:
        subprocess.run(program, shell=True, check=True)
        console.print("✅ LunarVim installation completed successfully", style="bold green")
    except subprocess.CalledProcessError as e:
        console.print(f"❌ Installation failed with exit code {e.returncode}", style="bold red")
        raise


if __name__ == "__main__":
    if TYPE_CHECKING:
        _main_protocol_check: InstallerPythonScriptMain = main
    pass
