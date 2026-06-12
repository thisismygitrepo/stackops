"""Install youtube-tui from crates.io with its native/default companion deps."""

import os
import platform
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Sequence

from rich.console import Console
from rich.panel import Panel

from stackops.utils.installer_utils.installer_main_protocol import InstallerPythonScriptMain
from stackops.utils.installer_utils.installer_cli import install_if_missing
from stackops.utils.cli_utils.command_lookup import check_tool_exists
from stackops.utils.source_of_truth import LINUX_INSTALL_PATH
from stackops.utils.schemas.installer.installer_types import InstallerData, get_os_name


YOUTUBE_TUI_REPO_URL = "https://github.com/Siriusmart/youtube-tui"
CRATE_NAME = "youtube-tui"
LINUX_REQUIRED_PACKAGES: dict[str, list[str]] = {
    "debian": [
        "curl",
        "build-essential",
        "pkg-config",
        "libssl-dev",
        "libmpv-dev",
        "libsixel-dev",
        "libxcb1-dev",
        "libxcb-render0-dev",
        "libxcb-shape0-dev",
        "libxcb-xfixes0-dev",
    ],
    "fedora": [
        "curl",
        "gcc",
        "gcc-c++",
        "make",
        "pkgconf-pkg-config",
        "openssl-devel",
        "mpv-devel",
        "libsixel-devel",
        "libxcb-devel",
    ],
    "arch": [
        "curl",
        "base-devel",
        "pkgconf",
        "openssl",
        "mpv",
        "libsixel",
        "libxcb",
    ],
    "suse": [
        "curl",
        "gcc",
        "gcc-c++",
        "make",
        "pkg-config",
        "libopenssl-devel",
        "mpv-devel",
        "libsixel-devel",
        "libxcb-devel",
    ],
    "alpine": [
        "curl",
        "build-base",
        "pkgconf",
        "openssl-dev",
        "mpv-dev",
        "libsixel-dev",
        "libxcb-dev",
    ],
}
LINUX_OPTIONAL_PACKAGES: dict[str, list[str]] = {
    "debian": ["mpv", "yt-dlp"],
    "fedora": ["mpv", "yt-dlp"],
    "arch": ["yt-dlp"],
    "suse": ["mpv", "yt-dlp"],
    "alpine": ["mpv", "yt-dlp"],
}
MACOS_REQUIRED_PACKAGES = ["pkg-config", "openssl", "mpv", "libsixel"]
MACOS_OPTIONAL_PACKAGES = ["yt-dlp"]


def _format_command(command: Sequence[str] | str) -> str:
    if isinstance(command, str):
        return command
    return " ".join(shlex.quote(part) for part in command)


def _run(
    command: Sequence[str] | str,
    console: Console,
    description: str,
    *,
    required: bool,
    env: dict[str, str] | None = None,
    shell: bool = False,
) -> bool:
    console.print(Panel(_format_command(command), title=description, expand=False))
    result = subprocess.run(command, shell=shell, text=True, check=False, env=env)
    if result.returncode == 0:
        return True

    message = f"{description} failed with exit code {result.returncode}"
    if required:
        raise RuntimeError(message)
    console.print(f"WARNING: {message}")
    return False


def _sudo_prefix() -> list[str]:
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        return []
    if shutil.which("sudo") is not None:
        return ["sudo"]
    return []


def _install_package_set(
    console: Console,
    *,
    family: str,
    package_manager: str,
    packages: list[str],
    required: bool,
) -> bool:
    if len(packages) == 0:
        return True

    sudo = _sudo_prefix()
    env = os.environ.copy()
    env.setdefault("DEBIAN_FRONTEND", "noninteractive")

    if package_manager == "nala":
        return _run([*sudo, "nala", "install", "-y", *packages], console, f"Install {family} packages", required=required, env=env)
    if package_manager == "apt-get":
        if required:
            _run([*sudo, "apt-get", "update"], console, "Update apt package index", required=False, env=env)
        return _run([*sudo, "apt-get", "install", "-y", *packages], console, f"Install {family} packages", required=required, env=env)
    if package_manager == "apt":
        if required:
            _run([*sudo, "apt", "update"], console, "Update apt package index", required=False, env=env)
        return _run([*sudo, "apt", "install", "-y", *packages], console, f"Install {family} packages", required=required, env=env)
    if package_manager == "dnf":
        return _run([*sudo, "dnf", "install", "-y", *packages], console, f"Install {family} packages", required=required, env=env)
    if package_manager == "yum":
        return _run([*sudo, "yum", "install", "-y", *packages], console, f"Install {family} packages", required=required, env=env)
    if package_manager == "pacman":
        return _run([*sudo, "pacman", "-S", "--needed", "--noconfirm", *packages], console, f"Install {family} packages", required=required, env=env)
    if package_manager == "zypper":
        return _run([*sudo, "zypper", "--non-interactive", "install", *packages], console, f"Install {family} packages", required=required, env=env)
    if package_manager == "apk":
        return _run([*sudo, "apk", "add", *packages], console, f"Install {family} packages", required=required, env=env)

    console.print(f"WARNING: unsupported package manager for {family} packages: {package_manager}")
    return False


def _detect_linux_package_manager() -> tuple[str, str] | None:
    for package_manager, family in [
        ("nala", "debian"),
        ("apt-get", "debian"),
        ("apt", "debian"),
        ("dnf", "fedora"),
        ("yum", "fedora"),
        ("pacman", "arch"),
        ("zypper", "suse"),
        ("apk", "alpine"),
    ]:
        if shutil.which(package_manager) is not None:
            return package_manager, family
    return None


def _install_linux_dependencies(console: Console) -> None:
    detected = _detect_linux_package_manager()
    if detected is None:
        console.print(
            "WARNING: no supported Linux package manager found; skipping native dependency installation."
        )
        return

    package_manager, family = detected
    required_packages = LINUX_REQUIRED_PACKAGES[family]
    optional_packages = LINUX_OPTIONAL_PACKAGES[family]
    _install_package_set(
        console,
        family="youtube-tui build/runtime",
        package_manager=package_manager,
        packages=required_packages,
        required=True,
    )
    for package_name in optional_packages:
        _install_package_set(
            console,
            family=f"optional youtube-tui companion: {package_name}",
            package_manager=package_manager,
            packages=[package_name],
            required=False,
        )


def _install_macos_dependencies(console: Console) -> None:
    if shutil.which("brew") is None:
        raise RuntimeError("The youtube-tui macOS installer requires Homebrew for native dependencies.")
    _run(["brew", "install", *MACOS_REQUIRED_PACKAGES], console, "Install youtube-tui build/runtime packages", required=True)
    for package_name in MACOS_OPTIONAL_PACKAGES:
        _run(["brew", "install", package_name], console, f"Install optional youtube-tui companion: {package_name}", required=False)


def _build_install_env() -> dict[str, str]:
    env = os.environ.copy()
    path_parts = [
        str(Path.home().joinpath(".cargo", "bin")),
        LINUX_INSTALL_PATH,
        env.get("PATH", ""),
    ]
    env["PATH"] = os.pathsep.join(part for part in path_parts if part != "")

    if platform.system() == "Darwin" and shutil.which("brew", path=env["PATH"]) is not None:
        openssl_prefix = subprocess.run(
            ["brew", "--prefix", "openssl@3"],
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        if openssl_prefix.returncode == 0:
            pkg_config_path = str(Path(openssl_prefix.stdout.strip()).joinpath("lib", "pkgconfig"))
            existing_pkg_config_path = env.get("PKG_CONFIG_PATH", "")
            env["PKG_CONFIG_PATH"] = os.pathsep.join(
                part for part in [pkg_config_path, existing_pkg_config_path] if part != ""
            )
    return env


def _which_in_env(binary_name: str, env: dict[str, str]) -> str | None:
    return shutil.which(binary_name, path=env.get("PATH"))


def _ensure_rust_toolchain(console: Console, env: dict[str, str]) -> None:
    if _which_in_env("cargo", env) is not None and _which_in_env("rustc", env) is not None:
        console.print("Rust toolchain already available.")
        return

    rustup_command = "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --no-modify-path"
    _run(rustup_command, console, "Install Rust toolchain with rustup", required=True, env=env, shell=True)
    if _which_in_env("cargo", env) is None or _which_in_env("rustc", env) is None:
        raise RuntimeError("Rust installation completed, but cargo/rustc were not found in the expected path.")


def _normalize_cargo_version(version: str | None) -> str | None:
    if version is None:
        return None
    stripped_version = version.strip()
    if stripped_version == "" or stripped_version.lower() == "latest":
        return None
    if stripped_version.startswith("v"):
        return stripped_version[1:]
    return stripped_version


def _cargo_install_youtube_tui(console: Console, env: dict[str, str], version: str | None, update: bool) -> None:
    cargo = _which_in_env("cargo", env)
    if cargo is None:
        raise RuntimeError("cargo was not found after Rust bootstrap.")

    install_root = Path(LINUX_INSTALL_PATH).parent
    install_root.mkdir(parents=True, exist_ok=True)

    cargo_version = _normalize_cargo_version(version)
    command = [cargo, "install", CRATE_NAME, "--root", str(install_root)]
    if cargo_version is not None:
        command.extend(["--version", cargo_version])
    if update or check_tool_exists(CRATE_NAME):
        command.append("--force")

    _run(command, console, "Install youtube-tui with cargo", required=True, env=env)


def _verify_native_pkg_config(console: Console, env: dict[str, str]) -> None:
    if _which_in_env("pkg-config", env) is None:
        console.print("WARNING: pkg-config is not available; native dependency verification skipped.")
        return
    for module_name in ["mpv", "libsixel", "xcb"]:
        result = subprocess.run(
            ["pkg-config", "--exists", module_name],
            text=True,
            check=False,
            env=env,
        )
        if result.returncode != 0:
            console.print(f"WARNING: pkg-config could not resolve {module_name}; cargo may fail to build default features.")


def _ensure_runtime_tools(console: Console, env: dict[str, str]) -> None:
    _ = env
    if not check_tool_exists("yt-dlp"):
        install_if_missing(which="yt-dlp", binary_name="yt-dlp", verbose=True)
    if shutil.which("mpv") is None and not check_tool_exists("mpv"):
        console.print("WARNING: mpv was not found after dependency installation; video playback may not work.")


def main(installer_data: InstallerData, version: str | None, update: bool) -> None:
    _ = installer_data
    console = Console()
    os_name = get_os_name()
    if os_name == "windows":
        raise NotImplementedError("youtube-tui is not intended for Windows by upstream.")

    console.print(
        Panel.fit(
            "\n".join(
                [
                    f"Version: {'latest crates.io release' if version is None else version}",
                    f"Source: {YOUTUBE_TUI_REPO_URL}",
                    "Installer: cargo install youtube-tui",
                    "Native deps: pkg-config, OpenSSL, libmpv/mpv, libsixel, libxcb",
                    "Runtime companions: mpv, yt-dlp",
                ]
            ),
            title="youtube-tui installer",
        )
    )

    if os_name == "linux":
        _install_linux_dependencies(console=console)
    elif os_name == "darwin":
        _install_macos_dependencies(console=console)
    else:
        raise NotImplementedError(f"youtube-tui installer does not support {platform.system()}.")

    env = _build_install_env()
    os.environ["PATH"] = env["PATH"]
    if "PKG_CONFIG_PATH" in env:
        os.environ["PKG_CONFIG_PATH"] = env["PKG_CONFIG_PATH"]

    _ensure_rust_toolchain(console=console, env=env)
    _verify_native_pkg_config(console=console, env=env)
    _cargo_install_youtube_tui(console=console, env=env, version=version, update=update)
    _ensure_runtime_tools(console=console, env=env)

    console.print(
        Panel.fit(
            f"youtube-tui installed to {Path(LINUX_INSTALL_PATH).joinpath(CRATE_NAME)}",
            title="youtube-tui post-install",
        )
    )


if __name__ == "__main__":
    if TYPE_CHECKING:
        _main_protocol_check: InstallerPythonScriptMain = main
