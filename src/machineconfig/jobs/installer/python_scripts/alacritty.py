"""alacritty"""

import platform
import subprocess
from rich import box
from rich.console import Console
from rich.panel import Panel
from machineconfig.utils.schemas.installer.installer_types import InstallerData


# config_dict: InstallerData = {"appName": "Alacritty", "repoURL": "CMD", "doc": "Terminal Console"}


def main(installer_data: InstallerData, version: str | None) -> None:
    console = Console()
    _ = installer_data
    console.print(
        Panel.fit(
            "\n".join([f"💻 Platform: {platform.system()}", f"🔄 Version: {'latest' if version is None else version}"]),
            title="🖥️  Alacritty Installer",
            border_style="cyan",
            box=box.ROUNDED,
        )
    )

    _ = version
    if platform.system() == "Windows":
        console.print("🪟 Installing Alacritty on Windows using Cargo...", style="bold")
        program = """

cargo install alacritty
mkdir -p $HOME/.config/alacritty/themes
git clone https://github.com/alacritty/alacritty-theme $HOME/.config/alacritty/themes

"""
    elif platform.system() in ["Linux", "Darwin"]:
        system_name = "Linux" if platform.system() == "Linux" else "macOS"
        console.print(f"🐧 Installing Alacritty on {system_name} using Cargo...", style="bold")
        program = """


cargo install alacritty
mkdir -p $HOME/.config/alacritty/themes
git clone https://github.com/alacritty/alacritty-theme $HOME/.config/alacritty/themes

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
                    "1️⃣  Install Alacritty using Cargo",
                    "2️⃣  Create config directories",
                    "3️⃣  Clone theme repository",
                ]
            ),
            title="ℹ️  Installation Plan",
            border_style="magenta",
            box=box.ROUNDED,
        )
    )

    console.print("🔄 EXECUTING | Running Alacritty installation...", style="bold yellow")
    try:
        subprocess.run(program, shell=True, text=True, check=True)
        console.print("✅ Alacritty installation completed successfully", style="bold green")
    except subprocess.CalledProcessError as e:
        console.print(f"❌ Installation failed with exit code {e.returncode}", style="bold red")
        raise


if __name__ == "__main__":
    pass
