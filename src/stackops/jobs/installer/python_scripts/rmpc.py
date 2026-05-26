"""Install rmpc and its common MPD/media companion tools using nala or brew."""

import json
import os
import platform
import re
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
NALA_OPTIONAL_PACKAGES = ["ffmpeg", "cava", "python3", "python3-pip", "python3-mutagen", "yt-dlp", "ueberzugpp"]
BREW_REQUIRED_PACKAGES = ["mpd", "mpc"]
BREW_OPTIONAL_PACKAGES = ["ffmpeg", "cava", "python-mutagen", "yt-dlp", "ueberzugpp"]
LINUX_MPD_SOCKET = "/run/mpd/socket"
MACOS_MPD_SOCKET = "~/.mpd/socket"


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


def _run_capture(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False)


def _python3_has_mutagen() -> bool:
    result = _run_capture(["python3", "-c", "import mutagen"])
    return result.returncode == 0


def _ensure_python3_mutagen(console: Console) -> None:
    if shutil.which("python3") is None:
        console.print("WARNING: python3 was not found; rmpc YouTube support will warn about python-mutagen.")
        return
    if _python3_has_mutagen():
        return

    install_commands = [
        "python3 -m pip install --user mutagen",
        "python3 -m pip install --user --break-system-packages mutagen",
    ]
    for command in install_commands:
        _run_shell(command, console, "Install mutagen for python3 used by rmpc", required=False)
        if _python3_has_mutagen():
            return

    console.print(
        "WARNING: python3 still cannot import mutagen; rmpc YouTube support may warn about python-mutagen."
    )


def _ron_string(value: str) -> str:
    return json.dumps(value)


def _upsert_ron_field(config_text: str, field_name: str, value_literal: str) -> str:
    field_pattern = re.compile(rf"(?m)^(\s*{re.escape(field_name)}\s*:\s*).*(,?)\s*$")
    if field_pattern.search(config_text):
        return field_pattern.sub(rf"\g<1>{value_literal},", config_text, count=1)

    open_tuple_match = re.search(r"\(\s*\n", config_text)
    if open_tuple_match is None:
        return f"(\n    {field_name}: {value_literal},\n)\n"
    insert_at = open_tuple_match.end()
    return f"{config_text[:insert_at]}    {field_name}: {value_literal},\n{config_text[insert_at:]}"


def _write_rmpc_youtube_config(console: Console, socket_path: str) -> None:
    config_path = Path.home().joinpath(".config", "rmpc", "config.ron")
    cache_dir = Path.home().joinpath(".cache", "rmpc")
    if config_path.exists():
        config_text = config_path.read_text(encoding="utf-8")
    else:
        exe_path = Path(LINUX_INSTALL_PATH).joinpath("rmpc")
        exe = str(exe_path) if exe_path.is_file() else shutil.which("rmpc")
        config_text = ""
        if exe is not None:
            result = subprocess.run([exe, "config"], capture_output=True, text=True, check=False)
            if result.returncode == 0 and result.stdout.strip() != "":
                config_text = result.stdout
            elif result.stderr.strip():
                console.print(result.stderr.strip())
        if config_text == "":
            config_text = "(\n)\n"

    config_text = _upsert_ron_field(
        config_text=config_text,
        field_name="address",
        value_literal=_ron_string(socket_path),
    )
    config_text = _upsert_ron_field(
        config_text=config_text,
        field_name="cache_dir",
        value_literal=_ron_string(str(cache_dir)),
    )

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(config_text, encoding="utf-8")
    cache_dir.mkdir(parents=True, exist_ok=True)
    console.print(f"Configured rmpc for local MPD socket: {socket_path}")


def _configure_linux_mpd_socket(console: Console) -> None:
    if shutil.which("sudo") is None and not (hasattr(os, "geteuid") and os.geteuid() == 0):
        console.print("WARNING: sudo is unavailable; cannot configure /etc/mpd.conf for local socket.")
        return

    script = f"""
set -e
conf=/etc/mpd.conf
socket={LINUX_MPD_SOCKET}
if [ ! -f "$conf" ]; then
  exit 0
fi
if ! grep -Eq '^[[:space:]]*bind_to_address[[:space:]]+"{re.escape(LINUX_MPD_SOCKET)}"' "$conf"; then
  cp -n "$conf" "$conf.stackops-rmpc.bak"
  printf '\\n# Added by stackops rmpc installer for local rmpc YouTube playback.\\nbind_to_address "{LINUX_MPD_SOCKET}"\\n' >> "$conf"
fi
"""
    _run_shell(f"{_sudo()}sh -c {json.dumps(script)}", console, "Configure MPD local socket", required=False)
    _run_shell(
        f"{_sudo()}systemctl restart mpd || {_sudo()}service mpd restart",
        console,
        "Restart MPD after socket configuration",
        required=False,
    )


def _configure_macos_mpd_socket(console: Console) -> None:
    Path.home().joinpath(".mpd").mkdir(parents=True, exist_ok=True)
    brew_prefix_result = _run_capture(["brew", "--prefix"])
    if brew_prefix_result.returncode != 0:
        console.print("WARNING: Could not resolve Homebrew prefix; skipping MPD socket config.")
        return

    mpd_conf = Path(brew_prefix_result.stdout.strip()).joinpath("etc", "mpd.conf")
    if not mpd_conf.exists():
        console.print(f"WARNING: Homebrew MPD config not found: {mpd_conf}")
        return

    config_text = mpd_conf.read_text(encoding="utf-8")
    if f'bind_to_address "{MACOS_MPD_SOCKET}"' not in config_text:
        backup_path = mpd_conf.with_suffix(mpd_conf.suffix + ".stackops-rmpc.bak")
        if not backup_path.exists():
            backup_path.write_text(config_text, encoding="utf-8")
        mpd_conf.write_text(
            config_text
            + f'\n# Added by stackops rmpc installer for local rmpc YouTube playback.\nbind_to_address "{MACOS_MPD_SOCKET}"\n',
            encoding="utf-8",
        )
    _run_shell("brew services restart mpd", console, "Restart Homebrew MPD after socket configuration", required=False)


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
        _configure_linux_mpd_socket(console=console)
        socket_path = LINUX_MPD_SOCKET
    else:
        _install_brew_companions(console=console)
        _configure_macos_mpd_socket(console=console)
        socket_path = MACOS_MPD_SOCKET
    _ensure_python3_mutagen(console=console)
    _write_rmpc_youtube_config(console=console, socket_path=socket_path)

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
