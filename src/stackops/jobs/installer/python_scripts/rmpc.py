"""Install rmpc and its common MPD/media companion tools using nala or brew."""

import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel

from stackops.jobs.installer.python_scripts.main_protocol import InstallerPythonScriptMain
from stackops.utils.installer_utils.installer_class import Installer
from stackops.utils.installer_utils.installer_locator_utils import LINUX_INSTALL_PATH
from stackops.utils.schemas.installer.installer_types import InstallerData, get_os_name


RMPC_REPO_URL = "https://github.com/mierak/rmpc"
RMPC_INSTALLER_DATA: InstallerData = {
    "appName": "rmpc",
    "license": "BSD-3-Clause",
    "repoURL": RMPC_REPO_URL,
    "doc": "A modern, configurable terminal based MPD client.",
    "fileNamePattern": {
        "amd64": {
            "linux": "rmpc-{version}-x86_64-unknown-linux-gnu.tar.gz",
            "darwin": "rmpc-{version}-x86_64-apple-darwin.tar.gz",
            "windows": None,
        },
        "arm64": {
            "linux": "rmpc-{version}-aarch64-unknown-linux-gnu.tar.gz",
            "darwin": "rmpc-{version}-aarch64-apple-darwin.tar.gz",
            "windows": None,
        },
    },
}

NALA_REQUIRED_PACKAGES = ["mpd", "mpc"]
NALA_OPTIONAL_PACKAGES = ["ffmpeg", "cava", "python3-mutagen", "yt-dlp", "ueberzugpp"]
BREW_REQUIRED_PACKAGES = ["mpd", "mpc"]
BREW_OPTIONAL_PACKAGES = ["ffmpeg", "cava", "yt-dlp", "ueberzugpp"]


def _sudo() -> str:
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        return ""
    if shutil.which("sudo") is not None:
        return "sudo "
    return ""


def _run_shell(command: str, console: Console, description: str, *, required: bool) -> bool:
    console.print(Panel(command, title=description, expand=False))
    result = subprocess.run(command, shell=True, text=True, check=False)
    if result.returncode == 0:
        return True
    message = f"{description} failed with exit code {result.returncode}"
    if required:
        raise RuntimeError(message)
    console.print(f"WARNING: {message}")
    return False


def _nala_install_command(packages: list[str]) -> str:
    package_args = " ".join(packages)
    return f"{_sudo()}nala install -y {package_args}"


def _brew_install_command(packages: list[str]) -> str:
    package_args = " ".join(packages)
    return f"brew install {package_args}"


def _install_nala_companions(console: Console) -> None:
    command = _nala_install_command(packages=NALA_REQUIRED_PACKAGES)
    _run_shell(command, console, "Install MPD companion packages", required=True)

    for optional_package in NALA_OPTIONAL_PACKAGES:
        _run_shell(
            _nala_install_command(packages=[optional_package]),
            console,
            f"Install optional rmpc companion package: {optional_package}",
            required=False,
        )


def _install_brew_companions(console: Console) -> None:
    command = _brew_install_command(packages=BREW_REQUIRED_PACKAGES)
    _run_shell(command, console, "Install MPD companion packages", required=True)

    for optional_package in BREW_OPTIONAL_PACKAGES:
        _run_shell(
            _brew_install_command(packages=[optional_package]),
            console,
            f"Install optional rmpc companion package: {optional_package}",
            required=False,
        )


def _bootstrap_config(console: Console) -> None:
    config_path = Path.home().joinpath(".config", "rmpc", "config.ron")
    if config_path.exists():
        console.print(f"rmpc config already exists: {config_path}")
        return

    exe_path = Path(LINUX_INSTALL_PATH).joinpath("rmpc")
    exe = str(exe_path) if exe_path.is_file() else shutil.which("rmpc")
    if exe is None:
        console.print("WARNING: rmpc executable was not found; skipping config bootstrap.")
        return

    result = subprocess.run([exe, "config"], capture_output=True, text=True, check=False)
    if result.returncode != 0 or result.stdout.strip() == "":
        console.print("WARNING: Could not generate default rmpc config.")
        if result.stderr.strip():
            console.print(result.stderr.strip())
        return

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(result.stdout, encoding="utf-8")
    console.print(f"Created default rmpc config: {config_path}")


def _normalize_release_version(version: str | None) -> str | None:
    if version is None:
        return None
    stripped_version = version.strip()
    if stripped_version == "" or stripped_version.lower() == "latest":
        return None
    if stripped_version.startswith("v"):
        return stripped_version
    return f"v{stripped_version}"


def main(installer_data: InstallerData, version: str | None, update: bool) -> None:
    _ = installer_data, update
    console = Console()
    system = platform.system()
    os_name = get_os_name()
    release_version = _normalize_release_version(version)

    if os_name == "linux":
        package_manager = "nala"
        if shutil.which("nala") is None:
            raise RuntimeError("This rmpc Linux installer requires nala.")
    elif os_name == "darwin":
        package_manager = "brew"
        if shutil.which("brew") is None:
            raise RuntimeError("This rmpc macOS installer requires brew.")
    else:
        raise NotImplementedError(f"This rmpc installer does not support {system}.")

    console.print(
        Panel.fit(
            "\n".join(
                [
                    f"Version: {'latest' if release_version is None else release_version}",
                    f"Source: {RMPC_REPO_URL}",
                    "Installer: upstream precompiled release archive",
                    f"Package manager: {package_manager}",
                ]
            ),
            title="rmpc installer",
        )
    )

    Installer(installer_data=RMPC_INSTALLER_DATA).install(version=release_version)

    if os_name == "linux":
        _install_nala_companions(console=console)
    else:
        _install_brew_companions(console=console)
    _bootstrap_config(console=console)

    console.print(
        Panel.fit(
            "\n".join(
                [
                    "rmpc is installed.",
                    "A working MPD server is still required before the TUI can play music.",
                    "Minimum upstream-supported MPD version: 0.23.5.",
                ]
            ),
            title="rmpc post-install",
        )
    )


if __name__ == "__main__":
    if TYPE_CHECKING:
        _main_protocol_check: InstallerPythonScriptMain = main
