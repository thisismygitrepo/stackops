import os
import platform
import shutil
import stat
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Final

from stackops.utils.installer_utils.install_request_logic import build_install_target, resolve_installer_pattern
from stackops.utils.installer_utils.installer_bulk_plan import holds_system_installer_lock
from stackops.utils.installer_utils.installer_class import Installer
from stackops.utils.installer_utils.installer_locator_utils import find_move_delete_linux, find_move_delete_windows
from stackops.utils.installer_utils.installer_main_protocol import InstallerPythonScriptMain
from stackops.utils.installer_utils.installer_runner import get_installers
from stackops.utils.schemas.installer.installer_types import InstallerData, get_normalized_arch, get_os_name
from stackops.utils.source_of_truth import INSTALL_VERSION_ROOT


installer_standard: InstallerData =    {
      "appName": "yazi",
      "license": "MIT",
      "repoURL": "https://github.com/sxyazi/yazi",
      "doc": "⚡ Blazing Fast Terminal File Manager.",
      "categoryLabels": ["file-managers"],
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
# catalog name of each previewer, and the executable it provides when that differs
PREVIEWERS: Final[tuple[tuple[str, str | None], ...]] = (
    ("glow", None),
    ("duckdb", None),
    ("poppler", "pdftotext"),
    ("chafa", None),
    ("jq", None),
    ("resvg", None),
    ("7zip", "7z"),
    ("file", None),
)
PLUGINS_SCRIPT: Final[str] = """
ya pkg add 'ndtoan96/ouch'  # make ouch default previewer in yazi for compressed files
ya pkg add 'AnirudhG07/rich-preview'  # rich-cli based previewer for yazi
ya pkg add 'Tyarel8/goto-drives'
ya pkg add 'uhs-robert/sshfs'
ya pkg add 'boydaihungst/file-extra-metadata'
ya pkg add 'wylie102/duckdb'
ya pkg install
"""


def _install_plugins() -> None:
    print("Cloning Yazi plugins repository...")
    if platform.system() == "Windows":
        yazi_plugins_dir = Path.home().joinpath("AppData", "Roaming", "yazi", "config")
    else:
        yazi_plugins_dir = Path.home().joinpath(".config", "yazi")
    yazi_plugins_path = yazi_plugins_dir.joinpath("plugins")

    def on_rm_error(_func: Callable[..., object], path: str, exc: BaseException) -> None:
        _ = _func, exc
        os.chmod(path, stat.S_IWRITE)
        try:
            os.unlink(path)
        except Exception:
            pass

    if yazi_plugins_path.is_file():
        yazi_plugins_path.unlink()
    elif yazi_plugins_path.is_dir():
        shutil.rmtree(yazi_plugins_path, onexc=on_rm_error)
        if yazi_plugins_path.exists():
            time.sleep(0.1)
            shutil.rmtree(yazi_plugins_path, ignore_errors=True)
    yazi_plugins_dir.mkdir(parents=True, exist_ok=True)
    import git
    from stackops.utils.code import run_shell_script

    git.Repo.clone_from("https://github.com/yazi-rs/plugins", yazi_plugins_path)
    run_shell_script(PLUGINS_SCRIPT, display_script=True, clean_env=False)


def main(installer_data: InstallerData, version: str | None, update: bool) -> None:
    _ = installer_data, update
    # one release archive carries both executables
    downloaded, installed_version = Installer(installer_data=installer_standard).binary_download(version=version)
    for exe_name, is_last in (("yazi", False), ("ya", True)):
        if platform.system() == "Windows":
            find_move_delete_windows(downloaded_file_path=downloaded, tool_name=exe_name, delete=is_last, rename_to=f"""{exe_name}.exe""")
        else:
            find_move_delete_linux(downloaded=downloaded, tool_name=exe_name, delete=is_last, rename_to=exe_name)
        INSTALL_VERSION_ROOT.joinpath(exe_name).parent.mkdir(parents=True, exist_ok=True)
        INSTALL_VERSION_ROOT.joinpath(exe_name).write_text(installed_version, encoding="utf-8")

    from stackops.utils.installer_utils.installer_cli import install_if_missing

    # the plugins are git repositories; on windows git can be missing
    install_if_missing(which="git", binary_name=None, verbose=True)

    operating_system = get_os_name()
    architecture = get_normalized_arch()
    catalog = {entry["appName"].casefold(): entry for entry in get_installers(os=operating_system, arch=architecture, which_cats=None)}
    one_at_a_time: list[tuple[str, str | None]] = []
    side_by_side: list[tuple[str, str | None]] = []
    for which, binary_name in PREVIEWERS:
        previewer = catalog.get(which)
        installer_value = None if previewer is None else resolve_installer_pattern(installer_data=previewer, operating_system=operating_system, architecture=architecture)
        uses_system_installer = (
            previewer is not None
            and installer_value is not None
            and holds_system_installer_lock(install_target=build_install_target(repo_url=previewer["repoURL"], installer_value=installer_value))
        )
        (one_at_a_time if uses_system_installer else side_by_side).append((which, binary_name))

    # downloads run side by side; previewers that go through the system package manager take turns; the plugins need neither
    jobs: list[Callable[[], object]] = [
        *(partial(install_if_missing, which=which, binary_name=binary_name, verbose=True) for which, binary_name in side_by_side),
        lambda: [install_if_missing(which=which, binary_name=binary_name, verbose=True) for which, binary_name in one_at_a_time],
        _install_plugins,
    ]
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        for submitted in [pool.submit(job) for job in jobs]:
            submitted.result()


if __name__ == "__main__":
    if TYPE_CHECKING:
        _main_protocol_check: InstallerPythonScriptMain = main
