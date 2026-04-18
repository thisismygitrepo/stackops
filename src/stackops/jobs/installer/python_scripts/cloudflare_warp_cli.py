
import platform
from typing import TYPE_CHECKING
import stackops.jobs.installer.linux_scripts as linux_scripts
from stackops.jobs.installer.python_scripts.main_protocol import (
    InstallerPythonScriptMain,
    
)
from stackops.utils.path_reference import get_path_reference_path
from stackops.utils.schemas.installer.installer_types import InstallerData


def main(installer_data: InstallerData, version: str | None, update: bool) -> str:
    _ = installer_data, version, update
    system = platform.system()
    if system == "Windows":
        raise NotImplementedError("Installer is not yet implemented for Windows.")
    elif system == "Linux":
        program = get_path_reference_path(
            module=linux_scripts,
            path_reference=linux_scripts.CLOUDFLARE_WARP_CLI_PATH_REFERENCE,
        ).read_text(encoding="utf-8")
    elif system == "Darwin":
        program = "brew install --cask cloudflare-warp"
    else:
        raise NotImplementedError(f"Unsupported platform: {system}")
    import subprocess
    subprocess.run(program, shell=True, check=True)
    return f"Cloudflare WARP CLI installed successfully on {system}."


if __name__ == "__main__":
    if TYPE_CHECKING:
        _main_protocol_check: InstallerPythonScriptMain = main
