from typing import TYPE_CHECKING, Callable
import platform
from stackops.jobs.installer.python_scripts.main_protocol import (
    InstallerPythonScriptMain,
    
)
from stackops.utils.installer_utils.installer_class import Installer
from stackops.utils.schemas.installer.installer_types import InstallerData


installer_standard: InstallerData =    {
      "appName": "yazi",
      "license": "MIT",
      "repoURL": "https://github.com/sxyazi/yazi",
      "doc": "⚡ Blazing Fast Terminal File Manager.",
      "fileNamePattern": {
        "amd64": {
          "linux": "yazi-x86_64-unknown-linux-musl.zip",
          "darwin": "yazi-x86_64-apple-darwin.zip",
          "windows": "yazi-x86_64-pc-windows-msvc.zip"
        },
        "arm64": {
          "linux": "yazi-aarch64-unknown-linux-musl.zip",
          "darwin": "yazi-aarch64-apple-darwin.zip",
          "windows": "yazi-aarch64-pc-windows-msvc.zip"
        }
      }
    }


def main(installer_data: InstallerData, version: str | None, update: bool) -> None:
    _ = installer_data, update
    inst = Installer(installer_data=installer_standard)
    inst.install(version=version)

    print("\n" * 5)
    print("Installing Yazi plugins and flavors...")
    installer_standard["appName"] = "ya"
    inst = Installer(installer_data=installer_standard)
    inst.install(version=version)

    print("\n" * 5)
    print("Cloning Yazi plugins and flavors repositories...")

    from pathlib import Path
    system_name = platform.system().lower()
    home_dir = Path.home()
    if system_name == "windows":
        yazi_plugins_dir = home_dir.joinpath("AppData", "Roaming", "yazi", "config")
    else:
        yazi_plugins_dir = home_dir.joinpath(".config", "yazi")
    
    yazi_plugins_path = yazi_plugins_dir.joinpath("plugins")
    yazi_flavours_path = yazi_plugins_dir.joinpath("flavors")
    import shutil
    import os
    import stat
    import time

    def on_rm_error(_func: Callable[..., object], path: str, exc: BaseException) -> None:
        _ = _func, exc
        os.chmod(path, stat.S_IWRITE)
        try:
            os.unlink(path)
        except Exception:
            pass

    def force_remove(path: Path) -> None:
        if path.exists():
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path, onexc=on_rm_error)
                if path.exists():
                    time.sleep(0.1)
                    shutil.rmtree(path, ignore_errors=True)
    force_remove(yazi_plugins_path)
    yazi_plugins_dir.mkdir(parents=True, exist_ok=True)
    from stackops.utils.installer_utils.installer_cli import install_if_missing
    # previewers:
    install_if_missing(which="glow", binary_name=None, verbose=True)
    install_if_missing(which="duckdb", binary_name=None, verbose=True)
    install_if_missing(which="poppler", binary_name="pdftotext", verbose=True)
    install_if_missing(which="viu", binary_name=None, verbose=True)
    install_if_missing(which="jq", binary_name=None, verbose=True)
    install_if_missing(which="resvg", binary_name=None, verbose=True)
    # on windows those are missing
    install_if_missing(which="git", binary_name=None, verbose=True)
    install_if_missing(which="7zip", binary_name="7z", verbose=True)
    install_if_missing(which="file", binary_name=None, verbose=True)
    import git
    git.Repo.clone_from("https://github.com/yazi-rs/plugins", yazi_plugins_path)
    force_remove(yazi_flavours_path)
    yazi_plugins_dir.mkdir(parents=True, exist_ok=True)
    git.Repo.clone_from("https://github.com/yazi-rs/flavors", yazi_flavours_path)
    script = """
ya pkg add 'ndtoan96/ouch'  # make ouch default previewer in yazi for compressed files
ya pkg add 'AnirudhG07/rich-preview'  # rich-cli based previewer for yazi
ya pkg add 'stelcodes/bunny'
ya pkg add 'Tyarel8/goto-drives'
ya pkg add 'uhs-robert/sshfs'
ya pkg add 'boydaihungst/file-extra-metadata'
ya pkg add 'wylie102/duckdb'
ya pkg install
"""
    from stackops.utils.code import run_shell_script
    run_shell_script(script, display_script=True, clean_env=False)


if __name__ == "__main__":
    if TYPE_CHECKING:
        _main_protocol_check: InstallerPythonScriptMain = main
    pass
