import os
import platform
from pathlib import Path
from typing import TYPE_CHECKING

from stackops.utils.installer_utils.installer_main_protocol import InstallerPythonScriptMain
from stackops.utils.installer_utils.installer_class import Installer
from stackops.utils.path_core import delete_path, move
from stackops.utils.schemas.installer.installer_types import InstallerData
from stackops.utils.source_of_truth import WINDOWS_INSTALL_PATH


FREE_LLMAPI_WINDOWS_ASSET_NAME = "FreeLLMAPI-{version}-win.zip"
FREE_LLMAPI_EXECUTABLE_NAME = "FreeLLMAPI.exe"
FREE_LLMAPI_ICU_DATA_NAME = "icudtl.dat"
FREE_LLMAPI_WINDOWS_WRAPPER_NAME = "freellmapi.cmd"
FREE_LLMAPI_STALE_WINDOWS_INSTALLER_NAME = "freellmapi.exe"
FREE_LLMAPI_WINDOWS_INSTALL_DIR_NAME = "FreeLLMAPI"


def _build_windows_installer_data(base_installer_data: InstallerData) -> InstallerData:
    return InstallerData(
        appName=base_installer_data["appName"],
        license=base_installer_data["license"],
        doc=base_installer_data["doc"],
        repoURL=base_installer_data["repoURL"],
        categoryLabels=base_installer_data["categoryLabels"],
        fileNamePattern={
            "amd64": {"linux": None, "windows": FREE_LLMAPI_WINDOWS_ASSET_NAME, "darwin": None},
            "arm64": {"linux": None, "windows": None, "darwin": None},
        },
    )


def _get_windows_install_root() -> Path:
    local_app_data_raw = os.environ.get("LOCALAPPDATA")
    local_app_data = Path(local_app_data_raw) if local_app_data_raw else Path.home().joinpath("AppData", "Local")
    return local_app_data.joinpath("Programs", FREE_LLMAPI_WINDOWS_INSTALL_DIR_NAME)


def _assert_windows_payload(extracted_dir: Path) -> None:
    executable = extracted_dir.joinpath(FREE_LLMAPI_EXECUTABLE_NAME)
    if not executable.is_file():
        raise FileNotFoundError(f"Expected {FREE_LLMAPI_EXECUTABLE_NAME} in extracted FreeLLMAPI payload: {extracted_dir}")
    icu_data = extracted_dir.joinpath(FREE_LLMAPI_ICU_DATA_NAME)
    if not icu_data.is_file():
        raise FileNotFoundError(
            f"Expected {FREE_LLMAPI_ICU_DATA_NAME} in extracted FreeLLMAPI payload: {extracted_dir}. "
            f"FreeLLMAPI is a portable Electron app; the bare executable alone cannot run."
        )


def _remove_stale_windows_apps_freellmapi_entry() -> None:
    stale_installer_path = Path(WINDOWS_INSTALL_PATH).joinpath(FREE_LLMAPI_STALE_WINDOWS_INSTALLER_NAME)
    if stale_installer_path.is_file():
        stale_installer_path.unlink(missing_ok=True)


def _write_windows_freellmapi_wrapper(target_executable: Path) -> Path:
    windows_install_path = Path(WINDOWS_INSTALL_PATH)
    windows_install_path.mkdir(parents=True, exist_ok=True)
    _remove_stale_windows_apps_freellmapi_entry()
    wrapper_path = windows_install_path.joinpath(FREE_LLMAPI_WINDOWS_WRAPPER_NAME)
    wrapper_path.write_text(
        f"""@echo off
\"{target_executable}\" %*
""",
        encoding="utf-8",
    )
    return wrapper_path


def _install_freellmapi_on_windows(installer_data: InstallerData, version: str | None) -> None:
    installer = Installer(installer_data=_build_windows_installer_data(base_installer_data=installer_data))
    extracted_dir, _resolved_version = installer.binary_download(version=version)
    try:
        _assert_windows_payload(extracted_dir=extracted_dir)
        install_root = _get_windows_install_root()
        if install_root.exists():
            delete_path(install_root, verbose=True)
        moved_root = move(extracted_dir, folder=install_root.parent, name=install_root.name, overwrite=True)
        target_executable = moved_root.joinpath(FREE_LLMAPI_EXECUTABLE_NAME)
        wrapper_path = _write_windows_freellmapi_wrapper(target_executable=target_executable)
        print(f"✅ FreeLLMAPI installed at {moved_root}")
        print(f"✅ Command wrapper installed at {wrapper_path}")
    finally:
        if extracted_dir.exists():
            delete_path(extracted_dir, verbose=True)


def main(installer_data: InstallerData, version: str | None, update: bool) -> None:
    _ = update
    match platform.system():
        case "Windows":
            _install_freellmapi_on_windows(installer_data=installer_data, version=version)
        case operating_system:
            raise NotImplementedError(f"FreeLLMAPI installer script is not supported on {operating_system}.")


if __name__ == "__main__":
    if TYPE_CHECKING:
        _main_protocol_check: InstallerPythonScriptMain = main
