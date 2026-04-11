"""vs code installer as per https://code.visualstudio.com/docs/setup/linux"""

import platform
from typing import TYPE_CHECKING
from rich import box
from rich.console import Console
from rich.panel import Panel
import machineconfig.jobs.installer.linux_scripts as linux_scripts
from machineconfig.jobs.installer.python_scripts.main_protocol import (
    InstallerPythonScriptMain,
    
)
from machineconfig.utils.path_reference import get_path_reference_path
from machineconfig.utils.schemas.installer.installer_types import InstallerData


def main(installer_data: InstallerData, version: str | None, update: bool) -> None:
    console = Console()
    _ = installer_data, update
    console.print(
        Panel.fit(
            "\n".join([f"🖥️  Platform: {platform.system()}", f"🔄 Version: {'latest' if version is None else version}"]),
            title="💻 VS Code Installer",
            border_style="blue",
            box=box.ROUNDED,
        )
    )

    if platform.system() == "Linux":
        console.print("🐧 Installing VS Code on Linux using official script...", style="bold")

        install_script = get_path_reference_path(
            module=linux_scripts,
            path_reference=linux_scripts.VSCODE_PATH_REFERENCE,
        ).read_text(
            encoding="utf-8"
        )
    elif platform.system() == "Darwin":
        console.print("🍎 Installing VS Code on macOS using Homebrew...", style="bold")
        install_script = """brew install --cask visual-studio-code"""
    elif platform.system() == "Windows":
        console.print("🪟 Installing VS Code on Windows using winget...", style="bold")
        install_script = """
winget install --no-upgrade --name "Microsoft Visual Studio Code" --Id "Microsoft.VisualStudioCode" --source winget --scope user --accept-package-agreements --accept-source-agreements

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
    _ = version

    # import subprocess
    # console.print("🔄 EXECUTING | Running VS Code installation...", style="bold yellow")
    # try:
    #     subprocess.run(install_script, shell=True, text=True, check=True)
    #     console.print("✅ VS Code installation completed successfully", style="bold green")
    # except subprocess.CalledProcessError as e:
    #     console.print(f"❌ Installation failed with exit code {e.returncode}", style="bold red")
    #     raise
    from machineconfig.utils.code import run_shell_script
    run_shell_script(install_script, display_script=True, clean_env=False)


if __name__ == "__main__":
    if TYPE_CHECKING:
        _main_protocol_check: InstallerPythonScriptMain = main
    pass
