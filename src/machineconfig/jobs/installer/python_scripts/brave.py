"""brave installer"""

import platform
import subprocess
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
            "\n".join([f"💻 Platform: {platform.system()}", f"🔄 Version: {'latest' if version is None else version}"]),
            title="🦁 Brave Browser Installer",
            border_style="orange1",
            box=box.ROUNDED,
        )
    )

    _ = version
    if platform.system() == "Windows":
        console.print("🪟 Installing Brave Browser on Windows using winget...", style="bold")
        program = """

winget install --no-upgrade --name "Brave"                        --Id "Brave.Brave"                --source winget --scope user --accept-package-agreements --accept-source-agreements

"""
    elif platform.system() in ["Linux", "Darwin"]:
        system_name = "Linux" if platform.system() == "Linux" else "macOS"
        console.print(f"🐧 Installing Brave Browser on {system_name}...", style="bold")
        import machineconfig.jobs.installer as module
        from pathlib import Path

        if platform.system() == "Linux":
            program = Path(module.__file__).parent.joinpath("linux_scripts/brave.sh").read_text(encoding="utf-8")
        else:  # Darwin/macOS
            program = "brew install --cask brave-browser"
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
                    "🔒 Built-in ad blocking",
                    "🛡️ Privacy-focused browsing",
                    "💨 Faster page loading",
                    "🪙 Optional crypto rewards",
                ]
            ),
            title="ℹ️  Brave Browser Features",
            border_style="magenta",
            box=box.ROUNDED,
        )
    )

    console.print("🔄 EXECUTING | Running Brave Browser installation...", style="bold yellow")
    from machineconfig.utils.code import print_code, run_shell_script
    try:
        print_code(code=program, lexer="shell", desc="Installation Script Preview")
        run_shell_script(program, display_script=True, clean_env=False)
        console.print("✅ Installation completed successfully!", style="bold green")
    except subprocess.CalledProcessError as e:
        console.print(f"❌ Installation failed with exit code {e.returncode}", style="bold red")
        raise


if __name__ == "__main__":
    pass


main: InstallerPythonScriptMain
