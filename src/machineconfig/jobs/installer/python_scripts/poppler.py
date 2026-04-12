import platform
from pathlib import Path
from typing import TYPE_CHECKING

import machineconfig.utils.path_core as path_core
from machineconfig.jobs.installer.python_scripts.main_protocol import (
    InstallerPythonScriptMain,
    
)
from machineconfig.utils.path_compression import delete_path
from machineconfig.utils.installer_utils.installer_class import Installer
from machineconfig.utils.path_extended import PathExtended
from machineconfig.utils.schemas.installer.installer_types import InstallerData


poppler_installer: InstallerData = {
    "appName": "poppler",
    "license": "GPL-2.0-or-later",
    "repoURL": "https://github.com/oschwartz10612/poppler-windows",
    "doc": "PDF rendering library - Windows builds.",
    "fileNamePattern": {
        "amd64": {
            "windows": "Release-{version}.zip",
            "linux": None,
            "darwin": None,
        },
        "arm64": {
            "windows": None,
            "linux": None,
            "darwin": None,
        }
    }
}


def _select_extracted_root(extracted_path: PathExtended) -> PathExtended:
    if extracted_path.is_file():
        return extracted_path
    children = [child for child in extracted_path.iterdir() if child.name not in {".", ".."}]
    if len(children) == 1 and children[0].is_dir():
        return PathExtended(children[0])
    return extracted_path


def main(installer_data: InstallerData, version: str | None, update: bool) -> None:
    _ = installer_data, update
    if platform.system() != "Windows":
        raise NotImplementedError("Poppler Windows installer is only supported on Windows.")

    installer = Installer(installer_data=poppler_installer)
    extracted_path, _version_to_be_installed = installer.binary_download(version=version)
    _ = _version_to_be_installed

    extracted_root = _select_extracted_root(extracted_path=PathExtended(extracted_path))
    target_root = PathExtended.home().joinpath(".local/share/poppler")
    if target_root.exists():
        delete_path(target_root, verbose=False)
    if extracted_root.is_file():
        raise FileNotFoundError(f"Expected extracted directory, got file: {extracted_root}")

    path_core.copy(extracted_root, path=target_root, overwrite=True)
    delete_path(extracted_path, verbose=False)


if __name__ == "__main__":
    if TYPE_CHECKING:
        _main_protocol_check: InstallerPythonScriptMain = main
    _ = Path
