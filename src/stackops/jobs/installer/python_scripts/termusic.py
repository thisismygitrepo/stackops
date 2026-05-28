"""Install termusic, termusic-server, and common audio/download dependencies."""

import os
import platform
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import stackops.utils.path_core as path_core
from rich.console import Console
from rich.panel import Panel

from stackops.jobs.installer.python_scripts.main_protocol import InstallerPythonScriptMain
from stackops.utils.installer_utils.installer_class import Installer
from stackops.utils.installer_utils.installer_locator_utils import LINUX_INSTALL_PATH, WINDOWS_INSTALL_PATH
from stackops.utils.path_core import delete_path
from stackops.utils.schemas.installer.installer_types import InstallerData, get_os_name
from stackops.utils.source_of_truth import INSTALL_VERSION_ROOT


TERMUSIC_REPO_URL = "https://github.com/tramhao/termusic"
TERMUSIC_INSTALLER_DATA: InstallerData = {
    "appName": "termusic",
    "license": "MIT and GPL-3.0",
    "repoURL": TERMUSIC_REPO_URL,
    "doc": "A terminal-based music player written in Rust.",
    "categoryLabels": ["media-audio-video"],
    "fileNamePattern": {
        "amd64": {
            "linux": "termusic-{version}-x86_64-linux.tar.xz",
            "darwin": "termusic-{version}-x86_64-macos.tar.xz",
            "windows": "termusic-{version}-x86_64-windows.zip",
        },
        "arm64": {
            "linux": "termusic-{version}-aarch64-linux.tar.xz",
            "darwin": "termusic-{version}-aarch64-macos.tar.xz",
            "windows": None,
        },
    },
}

DEBIAN_REQUIRED_PACKAGE_GROUPS = [
    ["libasound2t64", "libasound2", "libasound2-dev"],
    ["libdbus-1-3", "libdbus-1-dev"],
    ["libstdc++6"],
    ["libgstreamer1.0-0"],
    ["libmpv2", "mpv"],
]
DEBIAN_OPTIONAL_PACKAGES = [
    "yt-dlp",
    "ffmpeg",
    "mpv",
    "gstreamer1.0-tools",
    "gstreamer1.0-plugins-base",
    "gstreamer1.0-plugins-good",
    "gstreamer1.0-plugins-bad",
    "gstreamer1.0-plugins-ugly",
    "gstreamer1.0-libav",
    "libopus0",
    "libsixel-bin",
    "ueberzugpp",
]
ARCH_REQUIRED_PACKAGES = [
    "alsa-lib",
    "dbus",
    "gcc-libs",
    "gstreamer",
    "mpv",
]
ARCH_OPTIONAL_PACKAGES = [
    "yt-dlp",
    "ffmpeg",
    "gst-plugins-base",
    "gst-plugins-good",
    "gst-plugins-bad",
    "gst-plugins-ugly",
    "gst-libav",
    "opus",
    "libsixel",
    "ueberzugpp",
]
BREW_REQUIRED_PACKAGES = [
    "mpv",
    "gstreamer",
    "yt-dlp",
    "ffmpeg",
]
BREW_OPTIONAL_PACKAGES = [
    "opus",
    "libsixel",
    "ueberzugpp",
]
WINGET_OPTIONAL_PACKAGE_IDS = [
    "yt-dlp.yt-dlp",
    "Gyan.FFmpeg",
]
TERMUSIC_BINARIES = ["termusic", "termusic-server"]


def _sudo_prefix() -> list[str]:
    if os.name == "nt":
        return []
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        return []
    if shutil.which("sudo") is not None:
        return ["sudo"]
    return []


def _run_command(command: list[str], console: Console, description: str, *, required: bool) -> bool:
    console.print(Panel(shlex.join(command), title=description, expand=False))
    result = subprocess.run(command, text=True, check=False)
    if result.returncode == 0:
        return True
    message = f"{description} failed with exit code {result.returncode}"
    if required:
        raise RuntimeError(message)
    console.print(f"WARNING: {message}")
    return False


def _install_debian_package(package: str, console: Console, *, required: bool) -> bool:
    manager = "nala" if shutil.which("nala") is not None else None
    if manager is None and shutil.which("apt-get") is not None:
        manager = "apt-get"
    if manager is None and shutil.which("apt") is not None:
        manager = "apt"
    if manager is None:
        console.print("WARNING: nala/apt-get/apt not found; skipping Debian dependency installation.")
        return False
    return _run_command(
        [*_sudo_prefix(), manager, "install", "-y", package],
        console,
        f"Install termusic dependency: {package}",
        required=required,
    )


def _install_debian_package_options(packages: list[str], console: Console, *, required: bool) -> bool:
    for package in packages:
        if _install_debian_package(package, console, required=False):
            return True
    if required:
        package_options = ", ".join(packages)
        raise RuntimeError(f"Could not install any termusic dependency option: {package_options}")
    return False


def _install_arch_package(package: str, console: Console, *, required: bool) -> bool:
    return _run_command(
        [*_sudo_prefix(), "pacman", "-S", "--needed", "--noconfirm", package],
        console,
        f"Install termusic dependency: {package}",
        required=required,
    )


def _install_brew_package(package: str, console: Console, *, required: bool) -> bool:
    return _run_command(
        ["brew", "install", package],
        console,
        f"Install termusic dependency: {package}",
        required=required,
    )


def _install_winget_package(package_id: str, console: Console, *, required: bool) -> bool:
    return _run_command(
        [
            "winget",
            "install",
            "--id",
            package_id,
            "--exact",
            "--silent",
            "--accept-package-agreements",
            "--accept-source-agreements",
        ],
        console,
        f"Install termusic companion package: {package_id}",
        required=required,
    )


def _install_linux_dependencies(console: Console) -> None:
    if shutil.which("pacman") is not None:
        for package in ARCH_REQUIRED_PACKAGES:
            _install_arch_package(package, console, required=True)
        for package in ARCH_OPTIONAL_PACKAGES:
            _install_arch_package(package, console, required=False)
        return

    if shutil.which("nala") is None and shutil.which("apt-get") is None and shutil.which("apt") is None:
        console.print("WARNING: No supported Linux package manager found; installing binaries only.")
        return

    for packages in DEBIAN_REQUIRED_PACKAGE_GROUPS:
        _install_debian_package_options(packages, console, required=True)
    for package in DEBIAN_OPTIONAL_PACKAGES:
        _install_debian_package(package, console, required=False)


def _install_macos_dependencies(console: Console) -> None:
    if shutil.which("brew") is None:
        raise RuntimeError("This termusic macOS installer requires Homebrew for dependencies.")
    for package in BREW_REQUIRED_PACKAGES:
        _install_brew_package(package, console, required=True)
    for package in BREW_OPTIONAL_PACKAGES:
        _install_brew_package(package, console, required=False)


def _install_windows_dependencies(console: Console) -> None:
    if shutil.which("winget") is None:
        console.print("WARNING: winget not found; skipping Windows companion dependency installation.")
        return
    for package_id in WINGET_OPTIONAL_PACKAGE_IDS:
        _install_winget_package(package_id, console, required=False)


def _install_dependencies(console: Console) -> None:
    os_name = get_os_name()
    if os_name == "linux":
        _install_linux_dependencies(console)
        return
    if os_name == "darwin":
        _install_macos_dependencies(console)
        return
    if os_name == "windows":
        _install_windows_dependencies(console)
        return
    raise NotImplementedError(f"Termusic installer does not support {platform.system()}.")


def _normalize_release_version(version: str | None) -> str | None:
    if version is None:
        return None
    stripped_version = version.strip()
    if stripped_version == "" or stripped_version.lower() == "latest":
        return None
    if stripped_version.startswith("v"):
        return stripped_version
    return f"v{stripped_version}"


def _binary_file_name(binary_name: str) -> str:
    if platform.system() == "Windows":
        return f"{binary_name}.exe"
    return binary_name


def _install_target_dir() -> Path:
    if platform.system() == "Windows":
        return Path(WINDOWS_INSTALL_PATH)
    return Path(LINUX_INSTALL_PATH)


def _find_binary(downloaded: Path, binary_name: str) -> Path:
    file_name = _binary_file_name(binary_name)
    if downloaded.is_file() and downloaded.name == file_name:
        return downloaded
    matches = [path for path in downloaded.rglob(file_name) if path.is_file()]
    if len(matches) == 0:
        raise FileNotFoundError(f"Could not find {file_name} in {downloaded}")
    return max(matches, key=lambda path: path.stat().st_size)


def _install_binary(binary_path: Path, target_dir: Path, console: Console) -> Path:
    binary_path.chmod(0o755)
    installed_path = path_core.move(binary_path, folder=target_dir, overwrite=True, verbose=False)
    console.print(f"Installed {installed_path}")
    return installed_path


def _warn_missing_linux_libraries(installed_server: Path, console: Console) -> None:
    if platform.system() != "Linux" or shutil.which("ldd") is None:
        return
    result = subprocess.run(["ldd", str(installed_server)], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return
    missing_lines = [line.strip() for line in result.stdout.splitlines() if "not found" in line]
    if len(missing_lines) == 0:
        return
    console.print(
        Panel(
            "\n".join(missing_lines),
            title="WARNING: termusic-server has missing shared libraries",
            border_style="yellow",
        )
    )


def _write_installed_version(version_to_be_installed: str) -> None:
    for binary_name in TERMUSIC_BINARIES:
        version_path = INSTALL_VERSION_ROOT.joinpath(binary_name)
        version_path.parent.mkdir(parents=True, exist_ok=True)
        version_path.write_text(version_to_be_installed or "unknown", encoding="utf-8")


def _install_termusic_binaries(version: str | None, console: Console) -> None:
    release_version = _normalize_release_version(version)
    installer = Installer(installer_data=TERMUSIC_INSTALLER_DATA)
    downloaded, version_to_be_installed = installer.binary_download(version=release_version)
    target_dir = _install_target_dir()
    target_dir.mkdir(parents=True, exist_ok=True)

    installed_paths: dict[str, Path] = {}
    try:
        for binary_name in TERMUSIC_BINARIES:
            binary_path = _find_binary(downloaded=downloaded, binary_name=binary_name)
            installed_paths[binary_name] = _install_binary(binary_path=binary_path, target_dir=target_dir, console=console)
    finally:
        delete_path(downloaded, verbose=False)

    _write_installed_version(version_to_be_installed=version_to_be_installed)
    installed_server = installed_paths.get("termusic-server")
    if installed_server is not None:
        _warn_missing_linux_libraries(installed_server=installed_server, console=console)


def main(installer_data: InstallerData, version: str | None, update: bool) -> None:
    _ = installer_data, update
    console = Console()
    console.print(
        Panel.fit(
            "\n".join(
                [
                    f"Platform: {platform.system()}",
                    f"Version: {'latest' if version is None else version}",
                    f"Source: {TERMUSIC_REPO_URL}",
                    "Installer: release archive plus dependency setup",
                ]
            ),
            title="termusic installer",
        )
    )

    _install_dependencies(console=console)
    _install_termusic_binaries(version=version, console=console)
    console.print(
        Panel.fit(
            "termusic and termusic-server are installed.",
            title="termusic post-install",
        )
    )


if __name__ == "__main__":
    if TYPE_CHECKING:
        _main_protocol_check: InstallerPythonScriptMain = main
