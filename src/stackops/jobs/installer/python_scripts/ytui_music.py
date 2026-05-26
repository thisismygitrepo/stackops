"""Install ytui-music and the runtime tools required by its release binary."""

import os
import platform
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Sequence

from rich.console import Console
from rich.panel import Panel

from stackops.jobs.installer.python_scripts.main_protocol import InstallerPythonScriptMain
from stackops.utils.installer_utils.installer_class import Installer
from stackops.utils.installer_utils.installer_locator_utils import LINUX_INSTALL_PATH
from stackops.utils.schemas.installer.installer_types import (
    CPU_ARCHITECTURES,
    OPERATING_SYSTEMS,
    InstallerData,
    get_normalized_arch,
    get_os_name,
)


YTUI_MUSIC_REPO_URL = "https://github.com/sudipghimire533/ytui-music"
YTUI_MUSIC_RELEASE_ASSET = "ytui_music-linux-amd64"
YTUI_MUSIC_BINARY_NAME = "ytui_music"
YTUI_MUSIC_ALIAS_NAME = "ytui-music"
YOUTUBE_DL_SHIM_MARKER = "Managed by stackops ytui_music installer"

APT_REQUIRED_PACKAGES = ("mpv", "libmpv1", "libssl3", "ffmpeg", "ca-certificates")
APT_OPTIONAL_PACKAGES = ("libmpv-dev",)
DNF_REQUIRED_PACKAGES = ("mpv", "mpv-libs", "openssl-libs", "ffmpeg", "ca-certificates")
PACMAN_REQUIRED_PACKAGES = ("mpv", "openssl", "ffmpeg", "ca-certificates")
ZYPPER_REQUIRED_PACKAGES = ("mpv", "libmpv1", "libopenssl3", "ffmpeg", "ca-certificates")

DEFAULT_MPV_OPTIONS = (
    "video=no",
    "cache=yes",
    "demuxer-readahead-secs=10",
    "hwdec=yes",
    "cache-pause-wait=10",
    "demuxer-cache-wait=no",
    "cache-on-disk=yes",
    "ytdl-format=worst",
)


def _empty_file_name_pattern() -> dict[CPU_ARCHITECTURES, dict[OPERATING_SYSTEMS, str | None]]:
    return {
        "amd64": {
            "linux": None,
            "darwin": None,
            "windows": None,
        },
        "arm64": {
            "linux": None,
            "darwin": None,
            "windows": None,
        },
    }


def _build_binary_installer_data(base_installer_data: InstallerData) -> InstallerData:
    file_name_pattern = _empty_file_name_pattern()
    file_name_pattern["amd64"]["linux"] = YTUI_MUSIC_RELEASE_ASSET
    return InstallerData(
        appName=YTUI_MUSIC_BINARY_NAME,
        license=base_installer_data["license"],
        doc=base_installer_data["doc"],
        repoURL=YTUI_MUSIC_REPO_URL,
        fileNamePattern=file_name_pattern,
    )


def _is_root() -> bool:
    geteuid = getattr(os, "geteuid", None)
    return callable(geteuid) and geteuid() == 0


def _with_sudo(command: Sequence[str]) -> list[str]:
    if _is_root():
        return list(command)
    if shutil.which("sudo") is not None:
        return ["sudo", *command]
    raise RuntimeError("Installing ytui-music system dependencies requires root or sudo.")


def _format_command(command: Sequence[str]) -> str:
    return " ".join(shlex.quote(part) for part in command)


def _run(command: Sequence[str], console: Console, description: str, *, required: bool) -> bool:
    console.print(Panel(_format_command(command), title=description, expand=False))
    result = subprocess.run(command, text=True, check=False)
    if result.returncode == 0:
        return True
    message = f"{description} failed with exit code {result.returncode}"
    if required:
        raise RuntimeError(message)
    console.print(f"WARNING: {message}")
    return False


def _run_capture(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False)


def _resolve_executable(name: str) -> Path | None:
    candidate_paths = (
        Path(LINUX_INSTALL_PATH).joinpath(name),
        Path("/usr/local/bin").joinpath(name),
        Path("/usr/bin").joinpath(name),
    )
    for candidate_path in candidate_paths:
        if candidate_path.is_file():
            return candidate_path
    resolved = shutil.which(name)
    if resolved is None:
        return None
    return Path(resolved)


def _ldconfig_output() -> str:
    ldconfig = shutil.which("ldconfig")
    if ldconfig is None:
        for candidate in ("/sbin/ldconfig", "/usr/sbin/ldconfig"):
            if Path(candidate).is_file():
                ldconfig = candidate
                break
    if ldconfig is None:
        return ""
    result = _run_capture([ldconfig, "-p"])
    if result.returncode != 0:
        return ""
    return result.stdout


def _common_library_paths(library_name: str) -> tuple[Path, ...]:
    arch_dirs = ("x86_64-linux-gnu", "aarch64-linux-gnu")
    base_dirs = [Path("/lib"), Path("/usr/lib"), Path("/lib64"), Path("/usr/lib64"), Path("/usr/local/lib")]
    for arch_dir in arch_dirs:
        base_dirs.extend([Path("/lib").joinpath(arch_dir), Path("/usr/lib").joinpath(arch_dir)])
    return tuple(base_dir.joinpath(library_name) for base_dir in base_dirs)


def _library_available(library_name: str) -> bool:
    if any(library_path.exists() for library_path in _common_library_paths(library_name)):
        return True
    return library_name in _ldconfig_output()


def _missing_system_requirements() -> list[str]:
    missing: list[str] = []
    if _resolve_executable("mpv") is None:
        missing.append("mpv executable")
    if _resolve_executable("ffmpeg") is None:
        missing.append("ffmpeg executable")
    if not _library_available("libmpv.so.1"):
        missing.append("libmpv.so.1")
    if not _library_available("libssl.so.3"):
        missing.append("libssl.so.3")
    return missing


def _package_manager() -> str | None:
    for command in ("nala", "apt-get", "dnf", "pacman", "zypper"):
        if shutil.which(command) is not None:
            return command
    return None


def _install_linux_packages(console: Console) -> None:
    manager = _package_manager()
    if manager is None:
        raise RuntimeError("Could not find nala, apt-get, dnf, pacman, or zypper to install ytui-music dependencies.")

    if manager == "nala":
        _run(_with_sudo(["nala", "update"]), console, "Refresh package metadata", required=False)
        _run(_with_sudo(["nala", "install", "-y", *APT_REQUIRED_PACKAGES]), console, "Install ytui-music runtime packages", required=True)
        _run(_with_sudo(["nala", "install", "-y", *APT_OPTIONAL_PACKAGES]), console, "Install optional ytui-music build headers", required=False)
        return

    if manager == "apt-get":
        _run(_with_sudo(["apt-get", "update"]), console, "Refresh package metadata", required=False)
        _run(
            _with_sudo(["env", "DEBIAN_FRONTEND=noninteractive", "apt-get", "install", "-y", *APT_REQUIRED_PACKAGES]),
            console,
            "Install ytui-music runtime packages",
            required=True,
        )
        _run(
            _with_sudo(["env", "DEBIAN_FRONTEND=noninteractive", "apt-get", "install", "-y", *APT_OPTIONAL_PACKAGES]),
            console,
            "Install optional ytui-music build headers",
            required=False,
        )
        return

    if manager == "dnf":
        _run(_with_sudo(["dnf", "install", "-y", *DNF_REQUIRED_PACKAGES]), console, "Install ytui-music runtime packages", required=True)
        return

    if manager == "pacman":
        _run(_with_sudo(["pacman", "-Sy", "--needed", "--noconfirm", *PACMAN_REQUIRED_PACKAGES]), console, "Install ytui-music runtime packages", required=True)
        return

    _run(_with_sudo(["zypper", "--non-interactive", "install", *ZYPPER_REQUIRED_PACKAGES]), console, "Install ytui-music runtime packages", required=True)


def _ensure_system_dependencies(console: Console) -> None:
    missing = _missing_system_requirements()
    if len(missing) == 0:
        console.print("ytui-music system dependencies are already available.")
        return

    console.print("Missing ytui-music system dependencies: " + ", ".join(missing))
    _install_linux_packages(console=console)
    missing_after_install = _missing_system_requirements()
    if len(missing_after_install) > 0:
        raise RuntimeError(
            "ytui-music runtime dependencies are still missing after package installation: "
            + ", ".join(missing_after_install)
        )


def _install_stackops_tool(which: str, binary_name: str | None, console: Console) -> bool:
    try:
        from stackops.utils.installer_utils.installer_cli import install_if_missing

        return install_if_missing(which=which, binary_name=binary_name, verbose=True)
    except Exception as exc:
        console.print(f"WARNING: Could not install {which}: {exc}")
        return False


def _write_youtube_dl_shim(ytdlp_path: Path, console: Console) -> Path:
    local_bin = Path(LINUX_INSTALL_PATH)
    local_bin.mkdir(parents=True, exist_ok=True)
    shim_path = local_bin.joinpath("youtube-dl")
    shim_content = "\n".join(
        [
            "#!/bin/sh",
            f"# {YOUTUBE_DL_SHIM_MARKER}",
            f"exec {shlex.quote(str(ytdlp_path))} \"$@\"",
            "",
        ]
    )

    if shim_path.exists() or shim_path.is_symlink():
        if shim_path.is_symlink() or YOUTUBE_DL_SHIM_MARKER in shim_path.read_text(encoding="utf-8", errors="ignore"):
            shim_path.unlink()
        else:
            console.print(f"Leaving existing youtube-dl executable in place: {shim_path}")
            return shim_path

    shim_path.write_text(shim_content, encoding="utf-8")
    shim_path.chmod(0o755)
    console.print(f"Installed youtube-dl compatibility shim: {shim_path}")
    return shim_path


def _ensure_youtube_downloader(console: Console) -> Path:
    ytdlp_path = _resolve_executable("yt-dlp")
    if ytdlp_path is None:
        _install_stackops_tool(which="yt-dlp", binary_name=None, console=console)
        ytdlp_path = _resolve_executable("yt-dlp")

    if ytdlp_path is not None:
        return _write_youtube_dl_shim(ytdlp_path=ytdlp_path, console=console)

    youtube_dl_path = _resolve_executable("youtube-dl")
    if youtube_dl_path is None:
        _install_stackops_tool(which="youtube-dl", binary_name=None, console=console)
        youtube_dl_path = _resolve_executable("youtube-dl")

    if youtube_dl_path is None:
        raise RuntimeError("ytui-music needs youtube-dl or a yt-dlp-backed youtube-dl shim.")
    return youtube_dl_path


def _ytui_config_dir() -> Path:
    if "YTUI_MUSIC_CONFIG_DIR" in os.environ:
        return Path(os.environ["YTUI_MUSIC_CONFIG_DIR"]).expanduser()
    if "YTUI_CONFIG_DIR" in os.environ:
        return Path(os.environ["YTUI_CONFIG_DIR"]).expanduser()
    if "XDG_CONFIG_HOME" in os.environ:
        return Path(os.environ["XDG_CONFIG_HOME"]).expanduser().joinpath("ytui_music")
    return Path.home().joinpath(".config", "ytui_music")


def _ensure_download_directory() -> Path:
    if "YTUI_MUSIC_DIR" in os.environ:
        music_dir = Path(os.environ["YTUI_MUSIC_DIR"]).expanduser()
    else:
        music_dir = Path.home().joinpath("Music")
    music_dir.mkdir(parents=True, exist_ok=True)
    return music_dir


def _mpv_script_opts_line(youtube_dl_path: Path) -> str:
    return f"script-opts=ytdl_hook-try_ytdl_first=yes,ytdl_hook-ytdl_path={youtube_dl_path}"


def _ensure_ytui_config(youtube_dl_path: Path, console: Console) -> None:
    config_dir = _ytui_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    music_dir = _ensure_download_directory()
    mpv_conf = config_dir.joinpath("mpv.conf")
    desired_script_opts = _mpv_script_opts_line(youtube_dl_path=youtube_dl_path)

    if not mpv_conf.exists():
        content = "\n".join([*DEFAULT_MPV_OPTIONS, desired_script_opts, ""])
        mpv_conf.write_text(content, encoding="utf-8")
        console.print(f"Created ytui-music mpv config: {mpv_conf}")
    else:
        config_text = mpv_conf.read_text(encoding="utf-8")
        default_script_opts = 'script-opts="ytdl_hook-try_ytdl_first=yes"'
        if "ytdl_hook-ytdl_path" not in config_text and default_script_opts in config_text:
            mpv_conf.write_text(config_text.replace(default_script_opts, desired_script_opts), encoding="utf-8")
            console.print(f"Updated ytui-music mpv config: {mpv_conf}")

    console.print(f"Ensured ytui-music config directory: {config_dir}")
    console.print(f"Ensured ytui-music download directory: {music_dir}")


def _ensure_hyphen_alias(console: Console) -> None:
    local_bin = Path(LINUX_INSTALL_PATH)
    binary_path = local_bin.joinpath(YTUI_MUSIC_BINARY_NAME)
    alias_path = local_bin.joinpath(YTUI_MUSIC_ALIAS_NAME)
    if not binary_path.is_file():
        raise RuntimeError(f"Expected ytui-music binary was not installed at {binary_path}")

    if alias_path.exists() or alias_path.is_symlink():
        if alias_path.is_symlink() and alias_path.resolve() == binary_path:
            return
        console.print(f"Leaving existing ytui-music alias in place: {alias_path}")
        return

    try:
        alias_path.symlink_to(binary_path.name)
    except OSError:
        alias_path.write_text(
            "\n".join(["#!/bin/sh", f'exec "$(dirname "$0")/{YTUI_MUSIC_BINARY_NAME}" "$@"', ""]),
            encoding="utf-8",
        )
        alias_path.chmod(0o755)
    console.print(f"Installed ytui-music compatibility alias: {alias_path}")


def _validate_binary_links(binary_path: Path) -> None:
    if shutil.which("ldd") is None:
        return
    result = _run_capture(["ldd", str(binary_path)])
    if result.returncode != 0:
        raise RuntimeError(f"Could not inspect ytui-music binary links: {result.stderr.strip()}")
    unresolved_lines = [line.strip() for line in result.stdout.splitlines() if "not found" in line]
    if len(unresolved_lines) > 0:
        raise RuntimeError("ytui-music binary has unresolved shared libraries: " + "; ".join(unresolved_lines))


def main(installer_data: InstallerData, version: str | None, update: bool) -> None:
    _ = version, update
    console = Console()
    system = platform.system()
    os_name = get_os_name()
    arch = get_normalized_arch()

    if os_name != "linux" or arch != "amd64":
        raise NotImplementedError(f"ytui-music only publishes a Linux amd64 release binary; detected {system} {arch}.")

    console.print(
        Panel.fit(
            "\n".join(
                [
                    f"Source: {YTUI_MUSIC_REPO_URL}",
                    f"Asset: {YTUI_MUSIC_RELEASE_ASSET}",
                    "Runtime: mpv/libmpv, OpenSSL 3, ffmpeg, yt-dlp/youtube-dl compatibility",
                ]
            ),
            title="ytui-music installer",
        )
    )

    _ensure_system_dependencies(console=console)
    youtube_dl_path = _ensure_youtube_downloader(console=console)
    _ensure_ytui_config(youtube_dl_path=youtube_dl_path, console=console)

    Installer(installer_data=_build_binary_installer_data(base_installer_data=installer_data)).install(version=None)
    binary_path = Path(LINUX_INSTALL_PATH).joinpath(YTUI_MUSIC_BINARY_NAME)
    _ensure_hyphen_alias(console=console)
    _validate_binary_links(binary_path=binary_path)

    console.print(
        Panel.fit(
            "\n".join(
                [
                    f"Installed binary: {binary_path}",
                    f"Compatibility alias: {Path(LINUX_INSTALL_PATH).joinpath(YTUI_MUSIC_ALIAS_NAME)}",
                    "Run with: ytui_music run",
                ]
            ),
            title="ytui-music installed",
        )
    )


if __name__ == "__main__":
    if TYPE_CHECKING:
        _main_protocol_check: InstallerPythonScriptMain = main
