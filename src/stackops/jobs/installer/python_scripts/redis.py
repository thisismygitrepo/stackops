"""nedis installer"""

import platform
import subprocess
from typing import TYPE_CHECKING
from rich import box
from rich.console import Console
from rich.panel import Panel
import stackops.jobs.installer.linux_scripts as linux_scripts
from stackops.jobs.installer.python_scripts.main_protocol import (
    InstallerPythonScriptMain,
    
)
from stackops.utils.path_reference import get_path_reference_path
from stackops.utils.schemas.installer.installer_types import InstallerData

# config_dict: InstallerData = {"appName": "Redis", "repoURL": "CMD", "doc": "submillisecond fast key-value db"}


def main(installer_data: InstallerData, version: str | None, update: bool) -> None:
    console = Console()
    _ = installer_data, update
    console.print(
        Panel.fit(
            "\n".join([f"💻 Platform: {platform.system()}", f"🔄 Version: {'latest' if version is None else version}"]),
            title="🗃️  Redis Installer",
            border_style="red",
            box=box.ROUNDED,
        )
    )

    _ = version
    if platform.system() == "Windows":
        error_msg = "Redis installation not supported on Windows through this installer"
        console.print(
            Panel.fit(
                "\n".join([error_msg, "💡 Consider using WSL2 or Docker to run Redis on Windows"]),
                title="❌ Error",
                subtitle="⚠️ Unsupported platform",
                border_style="red",
                box=box.ROUNDED,
            )
        )
        raise NotImplementedError(error_msg)
    elif platform.system() in ["Linux", "Darwin"]:
        system_name = "Linux" if platform.system() == "Linux" else "macOS"
        console.print(f"🐧 Installing Redis on {system_name} using installation script...", style="bold")
        if platform.system() == "Linux":
            program = get_path_reference_path(
                module=linux_scripts,
                path_reference=linux_scripts.REDIS_PATH_REFERENCE,
            ).read_text(
                encoding="utf-8"
            )
        else:  # Darwin/macOS
            program = "brew install redis"
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
                    "⚡ In-memory data structure store",
                    "🔑 Key-value database with optional persistence",
                    "🚀 Sub-millisecond response times",
                    "💾 Supports strings, lists, sets, sorted sets, hashes",
                    "🔄 Built-in replication and Lua scripting",
                ]
            ),
            title="ℹ️  Redis Features",
            border_style="magenta",
            box=box.ROUNDED,
        )
    )

    console.print("🔄 EXECUTING | Running Redis installation...", style="bold yellow")
    try:
        subprocess.run(program, shell=True, text=True, check=True)
        console.print("✅ Redis installation completed successfully", style="bold green")
    except subprocess.CalledProcessError as e:
        console.print(f"❌ Installation failed with exit code {e.returncode}", style="bold red")
        raise


if __name__ == "__main__":
    if TYPE_CHECKING:
        _main_protocol_check: InstallerPythonScriptMain = main
    pass
