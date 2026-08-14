import platform
from pathlib import Path

import stackops.utils.path_core as path_core
from stackops.utils.installer_utils.installer_class import Installer
from stackops.utils.path_core import delete_path
from stackops.utils.schemas.installer.installer_types import InstallerData
from stackops.utils.source_of_truth import LINUX_INSTALL_PATH, WINDOWS_INSTALL_PATH


def _build_release_installer_data(installer_data: InstallerData) -> InstallerData:
    release_installer_data = installer_data.copy()
    release_installer_data["fileNamePattern"] = {
        "amd64": {
            "linux": "rustdesk-server-linux-amd64.zip",
            "windows": "rustdesk-server-windows-x86_64-unsigned.zip",
            "darwin": None,
        },
        "arm64": {
            "linux": "rustdesk-server-linux-arm64v8.zip",
            "windows": None,
            "darwin": None,
        },
    }
    return release_installer_data


def _resolve_release_binaries(extracted_root: Path, binary_names: tuple[str, ...], suffix: str) -> dict[str, Path]:
    resolved_binaries: dict[str, Path] = {}
    for binary_name in binary_names:
        expected_name = f"{binary_name}{suffix}"
        matches = [candidate for candidate in extracted_root.rglob(expected_name) if candidate.is_file()]
        if len(matches) != 1:
            raise FileNotFoundError(f"Expected one {expected_name} in {extracted_root}, found {len(matches)}.")
        resolved_binaries[binary_name] = matches[0]
    return resolved_binaries


def main(installer_data: InstallerData, version: str | None, update: bool) -> None:
    _ = update
    match platform.system():
        case "Linux":
            install_root = Path(LINUX_INSTALL_PATH)
            executable_suffix = ""
        case "Windows":
            install_root = Path(WINDOWS_INSTALL_PATH)
            executable_suffix = ".exe"
        case operating_system:
            raise NotImplementedError(f"RustDesk Server is not published for {operating_system}.")

    binary_names = ("hbbs", "hbbr", "rustdesk-utils")
    release_installer_data = _build_release_installer_data(installer_data=installer_data)
    extracted_root, _resolved_version = Installer(installer_data=release_installer_data).binary_download(version=version)
    _ = _resolved_version
    try:
        if not extracted_root.is_dir():
            raise NotADirectoryError(f"Expected an extracted RustDesk Server archive, got {extracted_root}.")
        resolved_binaries = _resolve_release_binaries(
            extracted_root=extracted_root,
            binary_names=binary_names,
            suffix=executable_suffix,
        )
        install_root.mkdir(parents=True, exist_ok=True)
        for binary_path in resolved_binaries.values():
            if platform.system() == "Linux":
                binary_path.chmod(0o755)
            path_core.move(binary_path, folder=install_root, overwrite=True)
    finally:
        delete_path(extracted_root, verbose=False)
