"""Install rmpc and its common MPD/media companion tools using nala or brew."""

import json
import os
import platform
import re
import shlex
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
    "categoryLabels": ["media-audio-video"],
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
DEFAULT_MPD_ADDRESS = "127.0.0.1:6600"
YT_DLP_REMOTE_COMPONENT_ARGS = ["--remote-components", "ejs:github"]
LINUX_MPD_SOCKET = "/run/mpd/socket"
LINUX_USER_MPD_SOCKET = str(Path.home().joinpath(".config", "mpd", "socket"))
LINUX_USER_MPD_MUSIC_DIR = Path.home().joinpath("Music")
LINUX_USER_RMPC_CACHE_DIR = LINUX_USER_MPD_MUSIC_DIR.joinpath("rmpc-cache")
DEFAULT_RMPC_CACHE_DIR = Path.home().joinpath(".cache", "rmpc")
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


def _mpd_endpoint_available(address: str) -> bool:
    if shutil.which("mpc") is None:
        return False
    resolved_address = str(Path(address).expanduser()) if address.startswith("~") else address
    result = _run_capture(["mpc", "-h", resolved_address, "status"])
    return result.returncode == 0


def _choose_rmpc_mpd_address(console: Console, socket_path: str) -> str:
    if _mpd_endpoint_available(socket_path):
        return socket_path
    if _mpd_endpoint_available(DEFAULT_MPD_ADDRESS):
        console.print(
            f"WARNING: MPD socket {socket_path} is unavailable; configuring rmpc for {DEFAULT_MPD_ADDRESS} instead."
        )
        console.print("WARNING: rmpc YouTube commands require an MPD Unix socket to add downloaded files.")
        return DEFAULT_MPD_ADDRESS
    console.print(
        f"WARNING: MPD did not answer on {socket_path} or {DEFAULT_MPD_ADDRESS}; using rmpc default address."
    )
    return DEFAULT_MPD_ADDRESS


def _python3_has_mutagen() -> bool:
    result = _run_capture(["python3", "-c", "import mutagen"])
    return result.returncode == 0


def _python3_executable() -> str | None:
    result = _run_capture(["python3", "-c", "import sys; print(sys.executable)"])
    if result.returncode != 0:
        return None
    executable = result.stdout.strip()
    return executable or None


def _python_executable_has_mutagen(python_executable: str) -> bool:
    result = _run_capture([python_executable, "-c", "import mutagen"])
    return result.returncode == 0


def _yt_dlp_python_executable() -> str | None:
    yt_dlp_path = shutil.which("yt-dlp")
    if yt_dlp_path is None:
        return None
    try:
        first_line = Path(yt_dlp_path).resolve().read_text(encoding="utf-8").splitlines()[0]
    except (IndexError, OSError, UnicodeDecodeError):
        return None
    if not first_line.startswith("#!") or "python" not in first_line:
        return None
    executable = first_line[2:].strip()
    executable_parts = shlex.split(executable)
    if len(executable_parts) >= 2 and Path(executable_parts[0]).name == "env":
        executable = shutil.which(executable_parts[1]) or executable_parts[1]
    return executable or None


def _install_mutagen_for_python(console: Console, python_executable: str, description: str) -> bool:
    install_commands = []
    if shutil.which("uv") is not None:
        install_commands.append(f"uv pip install --python {shlex.quote(python_executable)} mutagen")
    install_commands.extend(
        [
            f"{shlex.quote(python_executable)} -m pip install --user mutagen",
            f"{shlex.quote(python_executable)} -m pip install mutagen",
            f"{shlex.quote(python_executable)} -m pip install --user --break-system-packages mutagen",
        ]
    )

    for command in install_commands:
        _run_shell(command, console, description, required=False)
        if _python_executable_has_mutagen(python_executable):
            return True
    return False


def _ensure_python3_mutagen(console: Console) -> None:
    if shutil.which("python3") is None:
        console.print("WARNING: python3 was not found; rmpc YouTube support will warn about python-mutagen.")
        return

    python_executable = _python3_executable()
    if python_executable is not None and not _python_executable_has_mutagen(python_executable):
        _install_mutagen_for_python(console, python_executable, "Install mutagen for python3 used by rmpc")

    yt_dlp_python_executable = _yt_dlp_python_executable()
    if yt_dlp_python_executable is not None and not _python_executable_has_mutagen(yt_dlp_python_executable):
        _install_mutagen_for_python(
            console,
            yt_dlp_python_executable,
            "Install mutagen for the yt-dlp Python environment used by rmpc",
        )

    if not _python3_has_mutagen():
        console.print(
            "WARNING: python3 still cannot import mutagen; rmpc YouTube support may warn about python-mutagen."
        )
    if yt_dlp_python_executable is not None and not _python_executable_has_mutagen(yt_dlp_python_executable):
        console.print("WARNING: yt-dlp still cannot import mutagen; rmpc YouTube downloads may fail.")


def _ron_string(value: str) -> str:
    return json.dumps(value)


def _ron_string_list(value: list[str]) -> str:
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


def _write_rmpc_youtube_config(console: Console, mpd_address: str, cache_dir: Path | None = None) -> None:
    config_path = Path.home().joinpath(".config", "rmpc", "config.ron")
    resolved_cache_dir = cache_dir or DEFAULT_RMPC_CACHE_DIR
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
        value_literal=_ron_string(mpd_address),
    )
    config_text = _upsert_ron_field(
        config_text=config_text,
        field_name="cache_dir",
        value_literal=_ron_string(str(resolved_cache_dir)),
    )
    config_text = _upsert_ron_field(
        config_text=config_text,
        field_name="extra_yt_dlp_args",
        value_literal=_ron_string_list(YT_DLP_REMOTE_COMPONENT_ARGS),
    )

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(config_text, encoding="utf-8")
    resolved_cache_dir.mkdir(parents=True, exist_ok=True)
    console.print(f"Configured rmpc MPD address: {mpd_address}")


def _write_default_user_mpd_config(config_path: Path) -> None:
    mpd_data_dir = Path.home().joinpath(".local", "share", "mpd")
    mpd_state_dir = Path.home().joinpath(".local", "state", "mpd")
    config_text = "\n".join(
        [
            f'music_directory "{LINUX_USER_MPD_MUSIC_DIR}"',
            f'playlist_directory "{mpd_data_dir.joinpath("playlists")}"',
            f'db_file "{mpd_data_dir.joinpath("database")}"',
            f'log_file "{mpd_state_dir.joinpath("log")}"',
            f'pid_file "{mpd_state_dir.joinpath("pid")}"',
            f'state_file "{mpd_state_dir.joinpath("state")}"',
            f'sticker_file "{mpd_data_dir.joinpath("sticker.sql")}"',
            "",
            f'bind_to_address "{LINUX_USER_MPD_SOCKET}"',
            'auto_update "yes"',
            "",
        ]
    )
    config_path.write_text(config_text, encoding="utf-8")


def _configure_linux_user_mpd_socket(console: Console) -> str | None:
    if _mpd_endpoint_available(LINUX_USER_MPD_SOCKET):
        return LINUX_USER_MPD_SOCKET
    if shutil.which("mpd") is None:
        return None

    mpd_config_dir = Path.home().joinpath(".config", "mpd")
    mpd_data_dir = Path.home().joinpath(".local", "share", "mpd")
    mpd_state_dir = Path.home().joinpath(".local", "state", "mpd")
    config_path = mpd_config_dir.joinpath("mpd.conf")
    mpd_config_dir.mkdir(parents=True, exist_ok=True)
    mpd_data_dir.joinpath("playlists").mkdir(parents=True, exist_ok=True)
    mpd_state_dir.mkdir(parents=True, exist_ok=True)
    LINUX_USER_MPD_MUSIC_DIR.mkdir(parents=True, exist_ok=True)
    LINUX_USER_RMPC_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    if config_path.exists():
        config_text = config_path.read_text(encoding="utf-8")
        if f'bind_to_address "{LINUX_USER_MPD_SOCKET}"' not in config_text:
            config_path.write_text(
                config_text
                + f'\n# Added by stackops rmpc installer for local rmpc YouTube playback.\nbind_to_address "{LINUX_USER_MPD_SOCKET}"\n',
                encoding="utf-8",
            )
    else:
        _write_default_user_mpd_config(config_path=config_path)

    if shutil.which("systemctl") is not None:
        _run_shell("systemctl --user start mpd", console, "Start user MPD socket service", required=False)
        if _mpd_endpoint_available(LINUX_USER_MPD_SOCKET):
            return LINUX_USER_MPD_SOCKET

    _run_shell(f"mpd {shlex.quote(str(config_path))}", console, "Start user MPD socket daemon", required=False)
    if _mpd_endpoint_available(LINUX_USER_MPD_SOCKET):
        return LINUX_USER_MPD_SOCKET
    return None


def _configure_linux_mpd_socket(console: Console) -> None:
    if _mpd_endpoint_available(LINUX_MPD_SOCKET):
        return

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
    if _mpd_endpoint_available(MACOS_MPD_SOCKET):
        return

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

    cache_dir = DEFAULT_RMPC_CACHE_DIR
    if os_name == "linux":
        _install_nala_companions(console=console)
        user_socket_path = _configure_linux_user_mpd_socket(console=console)
        if user_socket_path is None:
            _configure_linux_mpd_socket(console=console)
            socket_path = LINUX_MPD_SOCKET
        else:
            socket_path = user_socket_path
            cache_dir = LINUX_USER_RMPC_CACHE_DIR
    else:
        _install_brew_companions(console=console)
        _configure_macos_mpd_socket(console=console)
        socket_path = MACOS_MPD_SOCKET
    mpd_address = _choose_rmpc_mpd_address(console=console, socket_path=socket_path)
    _ensure_python3_mutagen(console=console)
    _write_rmpc_youtube_config(console=console, mpd_address=mpd_address, cache_dir=cache_dir)

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
