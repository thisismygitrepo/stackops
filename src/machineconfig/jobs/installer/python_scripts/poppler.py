import platform
from pathlib import Path
from typing import TYPE_CHECKING

from machineconfig.jobs.installer.python_scripts.main_protocol import (
    InstallerPythonScriptMain,
    
)
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
            "macos": None,
        },
        "arm64": {
            "windows": None,
            "linux": None,
            "macos": None,
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
        target_root.delete(sure=True, verbose=False)
    if extracted_root.is_file():
        raise FileNotFoundError(f"Expected extracted directory, got file: {extracted_root}")

    extracted_root.copy(path=target_root, overwrite=True)
    extracted_path.delete(sure=True, verbose=False)


if __name__ == "__main__":
    if TYPE_CHECKING:
        _main_protocol_check: InstallerPythonScriptMain = main
    _ = Path
