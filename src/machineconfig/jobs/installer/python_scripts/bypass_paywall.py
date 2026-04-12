# import matplotlib.pyplot as plt

# from platform import system
from pathlib import Path
from typing import TYPE_CHECKING

import machineconfig.utils.path_compression as path_compression
from rich import box
from rich.console import Console
from rich.panel import Panel
from machineconfig.jobs.installer.python_scripts.main_protocol import (
    InstallerPythonScriptMain,
    
)
from machineconfig.utils.schemas.installer.installer_types import InstallerData
import machineconfig.utils.path_core as path_core


# config_dict: InstallerData = {
#     "appName": "bypass-paywalls-chrome",
#     "repoURL": "https://github.com/iamadamdev/bypass-paywalls-chrome",
#     "doc": """Plugin for chrome to bypass paywalls""",
# }


def main(installer_data: InstallerData, version: str | None, update: bool) -> str:
    console = Console()
    _ = installer_data, update
    console.print(
        Panel.fit(
            "\n".join([f"🔄 Version: {'latest' if version is None else version}"]),
            title="🔓 Bypass Paywall Installer",
            border_style="cyan",
            box=box.ROUNDED,
        )
    )

    _ = version
    folder = r"C:\\"
    folder_path = Path(folder)

    console.print("📥 Downloading extension from GitHub repository...", style="bold")
    downloaded_archive = path_core.download("https://github.com/iamadamdev/bypass-paywalls-chrome/archive/master.zip", folder=folder_path)
    path_compression.unzip_path(
        downloaded_archive,
        folder=folder_path,
        path=None,
        name=None,
        verbose=True,
        content=True,
        inplace=False,
        overwrite=False,
        orig=False,
        pwd=None,
        tmp=False,
        pattern=None,
        merge=False,
    )
    extension_folder = folder_path.joinpath("bypass-paywalls-chrome-master")

    console.print(
        Panel.fit(
            "\n".join(
                [
                    f"📂 Location: {extension_folder}",
                    "ℹ️  Next steps:",
                    "1️⃣  Open Chrome and navigate to chrome://extensions",
                    "2️⃣  Enable Developer Mode (toggle in top right)",
                    "3️⃣  Click 'Load unpacked' and select the extension folder",
                ]
            ),
            title="✅ Extension Ready",
            border_style="green",
            box=box.ROUNDED,
        )
    )

    return ""


if __name__ == "__main__":
    if TYPE_CHECKING:
        _main_protocol_check: InstallerPythonScriptMain = main
    pass
