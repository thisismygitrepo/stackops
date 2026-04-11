import platform
from typing import TYPE_CHECKING
from rich import box
from rich.console import Console
from rich.panel import Panel
import machineconfig.jobs.installer.linux_scripts as linux_scripts
import machineconfig.jobs.installer.powershell_scripts as powershell_scripts
from machineconfig.jobs.installer.python_scripts.main_protocol import InstallerPythonScriptMain
from machineconfig.utils.schemas.installer.installer_types import InstallerData
from machineconfig.utils.path_reference import get_path_reference_path


def main(installer_data: InstallerData, version: str | None, update: bool) -> None:
    console = Console()
    _ = installer_data, update
    console.print(
        Panel.fit(
            "\n".join([f"💻 Platform: {platform.system()}", f"🔄 Version: {'latest' if version is None else version}"]),
            title="🔧 ABC Installer",
            border_style="blue",
            box=box.ROUNDED,
        )
    )

    _ = version
    if platform.system() == "Windows":
        console.print("🪟 Installing ABC on Windows using winget...", style="bold")
        script = get_path_reference_path(module=powershell_scripts, path_reference=powershell_scripts.SYSABC_PATH_REFERENCE)
        program = script.read_text(encoding="utf-8")
    elif platform.system() == "Linux":
        console.print("🐧 Installing ABC on Linux...", style="bold")
        script = get_path_reference_path(module=linux_scripts, path_reference=linux_scripts.SYSABC_UBUNTU_PATH_REFERENCE)
        program = script.read_text(encoding="utf-8")
    elif platform.system() == "Darwin":
        console.print("🍎 Installing ABC on macOS...", style="bold")
        script = get_path_reference_path(module=linux_scripts, path_reference=linux_scripts.SYSABC_MACOS_PATH_REFERENCE)
        program = script.read_text(encoding="utf-8")
    else:
        error_msg = f"Unsupported platform: {platform.system()}"
        console.print(Panel.fit("\n".join([error_msg]), title="❌ Error", subtitle="⚠️ Unsupported platform", border_style="red", box=box.ROUNDED))
        raise NotImplementedError(error_msg)
    from machineconfig.utils.code import print_code, run_shell_script

    print_code(code=program, lexer="shell", desc="Installation Script Preview")
    run_shell_script(program, display_script=True, clean_env=False)


if __name__ == "__main__":
    if TYPE_CHECKING:
        _main_protocol_check: InstallerPythonScriptMain = main
