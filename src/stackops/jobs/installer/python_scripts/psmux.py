import platform
from pathlib import Path
from typing import TYPE_CHECKING

from stackops.utils import path_core
from stackops.utils.installer_utils.installer_class import Installer
from stackops.utils.installer_utils.installer_main_protocol import InstallerPythonScriptMain
from stackops.utils.schemas.installer.installer_types import InstallerData
from stackops.utils.source_of_truth import WINDOWS_INSTALL_PATH


PSMUX_BINARY_NAMES: tuple[str, ...] = ("psmux.exe", "pmux.exe", "tmux.exe")
PSMUX_RELEASE_INSTALLER_DATA: InstallerData = {
    "appName": "psmux",
    "license": "MIT License",
    "repoURL": "https://github.com/psmux/psmux",
    "doc": "Native Windows tmux built in Rust.",
    "categoryLabels": ["terminal-workspaces", "windows-platform"],
    "fileNamePattern": {
        "amd64": {"linux": None, "darwin": None, "windows": "psmux-{version}-windows-x64.zip"},
        "arm64": {"linux": None, "darwin": None, "windows": "psmux-{version}-windows-arm64.zip"},
    },
}


def main(installer_data: InstallerData, version: str | None, update: bool) -> None:
    _ = installer_data, update
    if platform.system() != "Windows":
        raise NotImplementedError(f"""psmux is Windows-only; current system is {platform.system()}.""")
    downloaded, version_to_be_installed = Installer(installer_data=PSMUX_RELEASE_INSTALLER_DATA).binary_download(version=version)
    binaries: list[Path] = []
    for binary_name in PSMUX_BINARY_NAMES:
        matches = [path for path in downloaded.rglob(binary_name) if path.is_file()]
        if len(matches) != 1:
            raise FileNotFoundError(f"""Expected exactly one {binary_name} in {downloaded}, found {len(matches)}.""")
        binaries.append(matches[0])
    for binary in binaries:
        path_core.move(binary, folder=WINDOWS_INSTALL_PATH, overwrite=True)
    path_core.delete_path(downloaded, verbose=True)
    print(f"""✅ psmux {version_to_be_installed} installed {", ".join(PSMUX_BINARY_NAMES)} into {WINDOWS_INSTALL_PATH}""")


if TYPE_CHECKING:
    _main_protocol_check: InstallerPythonScriptMain = main
