"""Nerd Fonts installer - Cross-platform font installation."""

import os
import platform
import shutil
import subprocess
from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING

from rich import box
from rich.console import Console
from rich.panel import Panel

import stackops.jobs.installer.powershell_scripts as powershell_scripts
from stackops.jobs.installer.python_scripts.main_protocol import (
    InstallerPythonScriptMain,
)
from stackops.utils.accessories import randstr
from stackops.utils.installer_utils.installer_class import Installer
from stackops.utils.path_core import delete_path, tmpfile
from stackops.utils.path_reference import get_path_reference_path
from stackops.utils.schemas.installer.installer_types import InstallerData


nerd_fonts: InstallerData = {
    "appName": "Cascadia Code Nerd Font",
    "license": "MIT / SIL OFL 1.1",
    "repoURL": "https://github.com/ryanoasis/nerd-fonts",
    "doc": "Nerd Fonts is a project that patches developer targeted fonts with a high number of glyphs (icons)",
    "categoryLabels": ["terminals-shells"],
    "fileNamePattern": {
        "amd64": {
            "windows": "CascadiaCode.zip",
            "linux": "CascadiaCode.zip",
            "darwin": "CascadiaCode.zip",
        },
        "arm64": {
            "windows": "CascadiaCode.zip",
            "linux": "CascadiaCode.zip",
            "darwin": "CascadiaCode.zip",
        },
    },
}


console = Console()


def render_banner(message: str, title: str, border_style: str, box_style: box.Box) -> None:
    console.print(Panel.fit(message, title=title, border_style=border_style, box=box_style, padding=(1, 4)))


def _list_installed_fonts() -> list[str]:
    """Return installed font file base names on Windows."""
    try:
        cmd = [
            "powershell.exe",
            "-NoLogo",
            "-NonInteractive",
            "-Command",
            "Get-ChildItem -Path C:/Windows/Fonts -File | Select-Object -ExpandProperty BaseName",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)  # noqa: S603
        return [font.strip().replace("_", "") for font in res.stdout.splitlines() if font.strip() != ""]
    except Exception as exc:  # noqa: BLE001
        console.print(f"⚠️ Could not enumerate installed fonts (continuing with install). Reason: {exc}")
        return []


def _missing_required_fonts(installed_fonts: Iterable[str]) -> list[str]:
    """Check which Cascadia/Caskaydia font families are missing."""

    def _normalize(name: str) -> str:
        return name.lower().replace(" ", "").replace("_", "")

    installed_norm = [_normalize(font) for font in installed_fonts]
    requirements: list[tuple[str, str]] = [
        ("cascadiacode", "Cascadia Code family"),
        ("caskaydiacove", "Caskaydia Cove Nerd Font family"),
    ]

    missing: list[str] = []
    for needle, label in requirements:
        if not any(needle in font for font in installed_norm):
            missing.append(label)
    return missing


def _normalize_release_version(version: str | None) -> str | None:
    if version is None:
        return None
    normalized = version.strip()
    if normalized == "":
        return None
    if normalized.lower() == "latest" or normalized.startswith("v"):
        return normalized
    return f"v{normalized}"


def _download_font_package(version: str | None) -> tuple[Path, str]:
    console.print("🔍 Downloading Nerd Fonts package...")
    return Installer(installer_data=nerd_fonts).binary_download(version=_normalize_release_version(version))


def _font_files(folder: Path) -> list[Path]:
    return sorted([*folder.rglob("*.ttf"), *folder.rglob("*.otf")])


def _cleanup_windows_payload(folder: Path) -> None:
    console.print("🧹 Cleaning up unnecessary files...")
    for pattern in ("*Windows*", "*readme*", "*LICENSE*"):
        for candidate in folder.glob(pattern):
            delete_path(candidate, verbose=True)


def _assert_font_payload(folder: Path) -> None:
    if not folder.exists():
        raise FileNotFoundError(f"Nerd Fonts payload does not exist: {folder}")
    if not folder.is_dir():
        raise FileNotFoundError(f"Expected extracted Nerd Fonts directory, got file: {folder}")
    if len(_font_files(folder)) == 0:
        raise FileNotFoundError(f"No .ttf or .otf files were found in Nerd Fonts payload: {folder}")


def _install_windows_nerd_fonts(version: str | None) -> None:
    console.print()
    render_banner("📦 INSTALLING NERD FONTS 📦", "Nerd Fonts Installer", "magenta", box.DOUBLE)
    console.print()

    installed = _list_installed_fonts()
    missing = _missing_required_fonts(installed)

    if len(missing) == 0:
        console.print("✅ Required Nerd Fonts already installed. Skipping download & install.")
        return

    console.print(f"🔍 Missing fonts detected: {', '.join(missing)}. Proceeding with installation...")
    folder, _version_to_be_installed = _download_font_package(version=version)

    try:
        _assert_font_payload(folder)
        _cleanup_windows_payload(folder)

        print("Fonts to be installed:")
        for font in _font_files(folder):
            print(f" - {font}")

        console.print("⚙️  Installing fonts via PowerShell...")
        file = tmpfile(name=randstr(), suffix=".ps1")

        raw_content = (
            get_path_reference_path(
                module=powershell_scripts,
                path_reference=powershell_scripts.INSTALL_FONTS_PATH_REFERENCE,
            )
            .read_text(encoding="utf-8")
            .replace(r".\fonts-to-be-installed", str(folder))
        )
        # PowerShell 5.1 can choke on certain unicode chars in some locales; keep ASCII only.
        content = "".join(ch for ch in raw_content if ord(ch) < 128)
        file.write_text(content, encoding="utf-8")

        try:
            subprocess.run(
                ["powershell.exe", "-executionpolicy", "Bypass", "-nologo", "-noninteractive", "-File", str(file)],
                check=True,
            )  # noqa: S603
        except subprocess.CalledProcessError as cpe:
            console.print(f"💥 Font installation script failed: {cpe}")
            raise
        finally:
            console.print("🗑️  Cleaning up temporary files...")
            if file.exists():
                delete_path(file, verbose=True)
    finally:
        if folder.exists():
            delete_path(folder, verbose=True)

    console.print()
    render_banner("✅ Nerd Fonts installation complete! ✅", "Nerd Fonts Installer", "green", box.DOUBLE)
    console.print()


def _platform_label(current_platform: str) -> str:
    if current_platform == "Linux":
        return "Linux"
    if current_platform == "Darwin":
        return "macOS"
    raise NotImplementedError(f"Unsupported platform: {current_platform}")


def _font_destination_dir(current_platform: str) -> Path:
    if current_platform == "Linux":
        xdg_data_home = os.environ.get("XDG_DATA_HOME")
        data_home = Path(xdg_data_home).expanduser() if xdg_data_home else Path.home().joinpath(".local/share")
        return data_home.joinpath("fonts")
    if current_platform == "Darwin":
        return Path.home().joinpath("Library/Fonts")
    raise NotImplementedError(f"Unsupported platform: {current_platform}")


def _print_nerd_font_features() -> None:
    console.print(
        Panel.fit(
            "\n".join(
                [
                    "🎨 Programming fonts patched with icons",
                    "🔣 Includes icons from popular sets (FontAwesome, Devicons, etc.)",
                    "🖥️  Perfect for terminals and coding environments",
                    "🧰 Works with many terminal applications and editors",
                ]
            ),
            title="ℹ️  Nerd Fonts Features",
            border_style="magenta",
            box=box.ROUNDED,
        )
    )


def _copy_fonts(source_dir: Path, font_dir: Path) -> int:
    font_files = _font_files(source_dir)
    if len(font_files) == 0:
        raise FileNotFoundError(f"No .ttf or .otf files were found in Nerd Fonts payload: {source_dir}")

    console.print(f"📁 Creating fonts directory: {font_dir}")
    font_dir.mkdir(parents=True, exist_ok=True)

    console.print("📋 Copying font files to fonts directory...")
    for font_file in font_files:
        shutil.copy2(font_file, font_dir.joinpath(font_file.name))
    return len(font_files)


def _refresh_linux_font_cache(font_dir: Path) -> None:
    if shutil.which("fc-cache") is None:
        console.print("⚠️ fc-cache not found; skipping font cache refresh.")
        return
    console.print("🔄 Updating font cache...")
    subprocess.run(["fc-cache", "-f", "-v", str(font_dir)], check=True)  # noqa: S603


def _install_local_nerd_fonts(current_platform: str, version: str | None) -> None:
    platform_label = _platform_label(current_platform=current_platform)
    console.print(f"Installing Nerd Fonts on {platform_label}...", style="bold")
    _print_nerd_font_features()

    folder, version_to_be_installed = _download_font_package(version=version)
    try:
        _assert_font_payload(folder)
        font_dir = _font_destination_dir(current_platform=current_platform)

        console.print(f"📦 PREPARED | Using CascadiaCode Nerd Font payload for {platform_label}")
        console.print(f"📂 Source directory: {folder}")
        console.print(f"🔄 Version resolved: {version_to_be_installed}")

        copied_count = _copy_fonts(source_dir=folder, font_dir=font_dir)
        if current_platform == "Linux":
            _refresh_linux_font_cache(font_dir=font_dir)

        console.print("✅ INSTALLATION COMPLETE | CascadiaCode Nerd Font has been installed", style="bold green")
        console.print(f"📋 Copied {copied_count} font files.")
        if current_platform == "Linux":
            console.print("ℹ️ To verify installation, run: fc-list | grep CaskaydiaCove")
        elif current_platform == "Darwin":
            console.print("ℹ️ To verify installation, run: system_profiler SPFontsDataType | grep -i CaskaydiaCove")
        console.print("💡 USE 'CaskaydiaCove Nerd Font' in VS Code and other applications")
        console.print("🔄 You may need to restart applications to see the new font")
    finally:
        if folder.exists():
            delete_path(folder, verbose=True)


def install_nerd_fonts(version: str | None = None) -> None:
    """Install Nerd Fonts for the current platform."""
    current_platform = platform.system()
    if current_platform == "Windows":
        _install_windows_nerd_fonts(version=version)
        return
    _install_local_nerd_fonts(current_platform=current_platform, version=version)


def main(installer_data: InstallerData, version: str | None, update: bool) -> None:
    """Main entry point for Nerd Fonts installation.

    Args:
        installer_data: Installation configuration data
        version: Specific version to install (None for latest)
    """
    _ = installer_data, update
    console.print(
        Panel.fit(
            "\n".join([f"💻 Platform: {platform.system()}", f"🔄 Version: {'latest' if version is None else version}"]),
            title="🔤 Nerd Fonts Installer",
            border_style="blue",
            box=box.ROUNDED,
        )
    )

    current_platform = platform.system()

    try:
        if current_platform == "Windows":
            console.print("🪟 Installing Nerd Fonts on Windows...", style="bold")
        install_nerd_fonts(version=version)
        if current_platform == "Windows":
            console.print(
                Panel.fit(
                    "\n".join(["💡 Restart terminal applications to see the new fonts."]),
                    title="✅ Nerd Fonts Installed",
                    border_style="green",
                    box=box.ROUNDED,
                )
            )
    except NotImplementedError as e:
        error_msg = str(e)
        console.print(
            Panel.fit(
                "\n".join([error_msg, "💡 Supported platforms are Windows, Linux, and macOS (Darwin)"]),
                title="❌ Error",
                subtitle="⚠️ Unsupported platform",
                border_style="red",
                box=box.ROUNDED,
            )
        )
        raise
    except subprocess.CalledProcessError as e:
        console.print(f"❌ Installation failed with exit code {e.returncode}", style="bold red")
        raise
    except Exception as e:  # noqa: BLE001
        error_msg = f"Nerd Fonts installation failed: {e}"
        if current_platform == "Windows":
            error_msg = f"Windows {error_msg}"
            console.print(
                Panel.fit(
                    "\n".join(
                        [
                            error_msg,
                            "💡 Try running as administrator or install manually from https://www.nerdfonts.com",
                        ]
                    ),
                    title="❌ Error",
                    subtitle="⚠️ Installation issue",
                    border_style="red",
                    box=box.ROUNDED,
                )
            )
        else:
            console.print(
                Panel.fit(
                    "\n".join([error_msg, "💡 Try running the installer again or install manually from https://www.nerdfonts.com"]),
                    title="❌ Error",
                    subtitle="⚠️ Installation issue",
                    border_style="red",
                    box=box.ROUNDED,
                )
            )
        raise RuntimeError(error_msg) from e


if __name__ == "__main__":
    if TYPE_CHECKING:
        _main_protocol_check: InstallerPythonScriptMain = main
    pass
