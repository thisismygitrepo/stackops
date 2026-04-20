import os
import platform
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from stackops.jobs.installer.python_scripts.main_protocol import InstallerPythonScriptMain
from stackops.utils.installer_utils.installer_class import Installer
from stackops.utils.path_core import delete_path
from stackops.utils.schemas.installer.installer_types import InstallerData
from stackops.utils.source_of_truth import WINDOWS_INSTALL_PATH


ORCA_WINDOWS_ASSET_NAME = "orca-windows-setup.exe"
ORCA_WINDOWS_WRAPPER_NAME = "orca.cmd"
ORCA_STALE_WINDOWS_INSTALLER_NAME = "orca.exe"


def _build_windows_installer_data(base_installer_data: InstallerData) -> InstallerData:
    return InstallerData(
        appName=base_installer_data["appName"],
        license=base_installer_data["license"],
        doc=base_installer_data["doc"],
        repoURL=base_installer_data["repoURL"],
        fileNamePattern={
            "amd64": {
                "linux": None,
                "windows": ORCA_WINDOWS_ASSET_NAME,
                "darwin": None,
            },
            "arm64": {
                "linux": None,
                "windows": None,
                "darwin": None,
            },
        },
    )


def _get_windows_orca_search_roots() -> tuple[Path, ...]:
    local_app_data_raw = os.environ.get("LOCALAPPDATA")
    local_app_data = Path(local_app_data_raw) if local_app_data_raw else Path.home().joinpath("AppData", "Local")
    search_roots: list[Path] = [
        local_app_data,
        local_app_data.joinpath("Programs"),
    ]
    for env_name in ("ProgramFiles", "ProgramFiles(x86)"):
        search_root_raw = os.environ.get(env_name)
        if not search_root_raw:
            continue
        search_root = Path(search_root_raw)
        if search_root not in search_roots:
            search_roots.append(search_root)
    return tuple(search_roots)


def _iter_orca_install_directories(search_root: Path) -> list[Path]:
    if not search_root.is_dir():
        return []
    candidate_dirs: list[Path] = []
    if "orca" in search_root.name.lower():
        candidate_dirs.append(search_root)
    for child in search_root.iterdir():
        if child.is_dir() and "orca" in child.name.lower():
            candidate_dirs.append(child)
    return candidate_dirs


def _get_direct_orca_executable(install_dir: Path) -> Path | None:
    for executable_name in ("Orca.exe", "orca.exe"):
        candidate = install_dir.joinpath(executable_name)
        if candidate.is_file():
            return candidate
    return None


def _get_nested_orca_executable(install_dir: Path) -> Path | None:
    nested_matches: list[Path] = []
    for executable_name in ("Orca.exe", "orca.exe"):
        nested_matches.extend(candidate for candidate in install_dir.rglob(executable_name) if candidate.is_file())
    if len(nested_matches) == 0:
        return None
    nested_matches.sort(key=lambda candidate: (len(candidate.relative_to(install_dir).parts), candidate.as_posix().lower()))
    return nested_matches[0]


def _find_installed_orca_executable(search_roots: tuple[Path, ...]) -> Path:
    nested_matches: list[Path] = []
    for search_root in search_roots:
        for install_dir in _iter_orca_install_directories(search_root=search_root):
            direct_match = _get_direct_orca_executable(install_dir=install_dir)
            if direct_match is not None:
                return direct_match
            nested_match = _get_nested_orca_executable(install_dir=install_dir)
            if nested_match is not None:
                nested_matches.append(nested_match)
    if len(nested_matches) > 0:
        nested_matches.sort(key=lambda candidate: (len(candidate.parts), candidate.as_posix().lower()))
        return nested_matches[0]
    raise FileNotFoundError("Could not find Orca.exe after running the Windows installer.")


def _remove_stale_windows_apps_orca_entry() -> None:
    stale_installer_path = Path(WINDOWS_INSTALL_PATH).joinpath(ORCA_STALE_WINDOWS_INSTALLER_NAME)
    if stale_installer_path.is_file():
        stale_installer_path.unlink(missing_ok=True)


def _write_windows_orca_wrapper(target_executable: Path) -> Path:
    windows_install_path = Path(WINDOWS_INSTALL_PATH)
    windows_install_path.mkdir(parents=True, exist_ok=True)
    _remove_stale_windows_apps_orca_entry()
    wrapper_path = windows_install_path.joinpath(ORCA_WINDOWS_WRAPPER_NAME)
    wrapper_path.write_text(
        f"""@echo off
\"{target_executable}\" %*
""",
        encoding="utf-8",
    )
    return wrapper_path


def _install_orca_on_windows(installer_data: InstallerData, version: str | None) -> None:
    installer = Installer(installer_data=_build_windows_installer_data(base_installer_data=installer_data))
    installer_path, _resolved_version = installer.binary_download(version=version)
    _ = _resolved_version
    if not installer_path.is_file():
        raise FileNotFoundError(f"Expected Orca Windows installer to be a file, got: {installer_path}")
    try:
        subprocess.run([str(installer_path), "/S"], text=True, check=True)
        orca_executable = _find_installed_orca_executable(search_roots=_get_windows_orca_search_roots())
        _write_windows_orca_wrapper(target_executable=orca_executable)
    finally:
        delete_path(installer_path, verbose=False)


def main(installer_data: InstallerData, version: str | None, update: bool) -> None:
    _ = update
    if platform.system() != "Windows":
        raise NotImplementedError("Orca Windows installer script is only supported on Windows.")
    _install_orca_on_windows(installer_data=installer_data, version=version)


if __name__ == "__main__":
    if TYPE_CHECKING:
        _main_protocol_check: InstallerPythonScriptMain = main
    pass
