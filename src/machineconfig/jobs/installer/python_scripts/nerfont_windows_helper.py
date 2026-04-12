"""
Windows-specific Nerd Fonts installation helper module.

This module provides Windows-specific functionality for installing Nerd Fonts
using PowerShell scripts and font enumeration.
"""

import subprocess
from typing import Iterable

from rich import box
from rich.console import Console
from rich.panel import Panel

import machineconfig.jobs.installer.powershell_scripts as powershell_scripts
from machineconfig.utils.path_core import delete_path, tmpfile
from machineconfig.utils.accessories import randstr
from machineconfig.utils.installer_utils.installer_class import Installer
from machineconfig.utils.path_reference import get_path_reference_path
from machineconfig.utils.schemas.installer.installer_types import InstallerData


nerd_fonts: InstallerData = {
    "appName": "Cascadia Code Nerd Font",
    "license": "MIT / SIL OFL 1.1",
    "repoURL": "https://github.com/ryanoasis/nerd-fonts",
    "doc": "Nerd Fonts is a project that patches developer targeted fonts with a high number of glyphs (icons)",
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
        }
    }
}


console = Console()


def render_banner(message: str, title: str, border_style: str, box_style: box.Box) -> None:
    console.print(Panel.fit(message, title=title, border_style=border_style, box=box_style, padding=(1, 4)))


def _list_installed_fonts() -> list[str]:
    """Return list of installed font file base names (without extension) on Windows.

    Uses PowerShell to enumerate C:\\Windows\\Fonts because Python on *nix host can't rely on that path.
    If PowerShell call fails (e.g. running on non-Windows), returns empty list so install proceeds.
    
    Returns:
        List of installed font base names
    """
    try:
        # Query only base names to make substring matching simpler; remove underscores like the PS script does.
        cmd = [
            "powershell.exe",
            "-NoLogo",
            "-NonInteractive",
            "-Command",
            "Get-ChildItem -Path C:/Windows/Fonts -File | Select-Object -ExpandProperty BaseName"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)  # noqa: S603 S607 (trusted command)
        fonts = [x.strip().replace("_", "") for x in res.stdout.splitlines() if x.strip() != ""]
        return fonts
    except Exception as exc:  # noqa: BLE001
        console.print(f"⚠️ Could not enumerate installed fonts (continuing with install). Reason: {exc}")
        return []


def _missing_required_fonts(installed_fonts: Iterable[str]) -> list[str]:
    """Check which feature fonts are missing from installed fonts.

    Args:
        installed_fonts: List of installed font names

    Returns:
        List of descriptions for missing font groups
    """

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


def install_nerd_fonts() -> None:
    """Install Nerd Fonts on Windows using PowerShell script.
    
    This function:
    1. Checks if required fonts are already installed
    2. Downloads the font package if needed
    3. Installs fonts using PowerShell script
    4. Cleans up temporary files
    
    Raises:
        subprocess.CalledProcessError: If PowerShell installation fails
    """
    console.print()
    render_banner("📦 INSTALLING NERD FONTS 📦", "Nerd Fonts Installer", "magenta", box.DOUBLE)
    console.print()
    
    installed = _list_installed_fonts()
    missing = _missing_required_fonts(installed)
    
    if len(missing) == 0:
        console.print("✅ Required Nerd Fonts already installed. Skipping download & install.")
        return
        
    console.print(f"🔍 Missing fonts detected: {', '.join(missing)}. Proceeding with installation...")
    console.print("🔍 Downloading Nerd Fonts package...")
    
    folder, _version_to_be_installed = Installer(installer_data=nerd_fonts).binary_download(version=None)

    console.print("🧹 Cleaning up unnecessary files...")
    for pattern in ("*Windows*", "*readme*", "*LICENSE*"):
        for candidate in folder.glob(pattern):
            delete_path(candidate, verbose=True)

    print("Fonts to be installed:")
    for font in (list(folder.glob("*.ttf")) + list(folder.glob("*.otf"))):
        print(f" - {font}")

    console.print("⚙️  Installing fonts via PowerShell...")
    file = tmpfile(name=randstr(), suffix=".ps1")

    raw_content = get_path_reference_path(
        module=powershell_scripts,
        path_reference=powershell_scripts.INSTALL_FONTS_PATH_REFERENCE,
    ).read_text(encoding="utf-8").replace(r".\fonts-to-be-installed", str(folder))
    # PowerShell 5.1 can choke on certain unicode chars in some locales; keep ASCII only.
    content = "".join(ch for ch in raw_content if ord(ch) < 128)
    file.write_text(content, encoding="utf-8")
    
    try:
        subprocess.run(rf"powershell.exe -executionpolicy Bypass -nologo -noninteractive -File {str(file)}", check=True)
    except subprocess.CalledProcessError as cpe:
        console.print(f"💥 Font installation script failed: {cpe}")
        raise
    finally:
        console.print("🗑️  Cleaning up temporary files...")
        if folder.exists():
            delete_path(folder, verbose=True)
        if file.exists():
            delete_path(file, verbose=True)

    console.print()
    render_banner("✅ Nerd Fonts installation complete! ✅", "Nerd Fonts Installer", "green", box.DOUBLE)
    console.print()


if __name__ == "__main__":
    install_nerd_fonts()
