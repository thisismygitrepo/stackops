"""
Installation Utilities
======================

This module provides functionality to download and install pre-checked applications.
"""

import platform
from concurrent.futures import ThreadPoolExecutor
from hashlib import file_digest
from pathlib import Path
from typing import cast

from rich.console import Console

from stackops.jobs.installer.checks.scan_history import ScanRun
from stackops.utils import path_core
from stackops.utils.source_of_truth import LINUX_INSTALL_PATH, WINDOWS_INSTALL_PATH

console = Console()


def download_google_drive_file(url: str) -> Path:
    """Downloads a file from Google Drive using gdown."""
    try:
        # Extract ID from URL
        # Assuming URL format like https://drive.google.com/file/d/FILE_ID/view or similar
        # or https://drive.google.com/uc?id=FILE_ID
        if "id=" in url:
            file_id = url.split("id=")[1].split("&")[0]
        elif "/d/" in url:
            file_id = url.split("/d/")[1].split("/")[0]
        else:
            # Fallback to gdown's auto detection or just pass URL
            file_id = url

        # Create a temporary directory for download
        output_dir = path_core.tmpdir(prefix="gdown_")
        # gdown.download returns the output filename when output is a directory path
        from gdown.download import download
        output_file = download(id=file_id, output=str(output_dir) + "/", quiet=False)

        if not output_file:
            raise ValueError(f"Download failed for {url}")

        return Path(cast(str, output_file))
    except Exception as e:
        raise RuntimeError(f"Failed to download from Google Drive: {e}") from e

def install_cli_app(app_url: str, expected_sha256: str | None, filename: str) -> bool:
    """Downloads and installs a CLI app."""
    try:
        if not app_url:
            return False
        if not expected_sha256:
            raise ValueError(f"""No SHA-256 recorded for {filename}.""")

        exe_path = download_google_drive_file(app_url)
        console.print(f"[green]Downloaded {exe_path.name}[/green]")
        with exe_path.open("rb") as downloaded_file:
            if file_digest(downloaded_file, "sha256").hexdigest() != expected_sha256:
                raise ValueError(f"""Downloaded {filename} does not match the scanned SHA-256.""")

        system = platform.system().lower()
        if system in ["linux", "darwin"]:
            exe_path.chmod(0o755) # Make executable
            # Move to local bin (requires user to have write access or sudo, which we can't easily do here without interaction)
            # Using LINUX_INSTALL_PATH is safer
            install_path = Path(LINUX_INSTALL_PATH)
            install_path.mkdir(parents=True, exist_ok=True)
            target = install_path / filename
            exe_path.rename(target)
            console.print(f"[green]Installed to {target}[/green]")
        elif system == "windows":
            install_path = Path(WINDOWS_INSTALL_PATH)
            install_path.mkdir(parents=True, exist_ok=True)
            target = install_path / filename
            # Use shutil.move or path_core.move
            path_core.move(exe_path, path=target, overwrite=True)
            console.print(f"[green]Installed to {target}[/green]")
        
        return True
    except Exception as e:
        console.print(f"[red]Failed to install app from {app_url}: {e}[/red]")
        return False

def download_safe_apps(name: str | None, run: ScanRun) -> bool:
    if run["status"] not in {"completed", "completed_with_errors"}:
        console.print("[red]Select a finished scan run before installing apps.[/red]")
        return False
    apps_to_install: list[tuple[str, str | None, str]] = []
    for target in run["targets"]:
        if target["record"] is None:
            continue
        app = target["record"]["app_data"]
        if (
            app["positive_pct"] == 0.0
            and app["verdict_engines"] > 0
            and app["app_url"]
            and (name is None or app["app_name"].casefold() == name.casefold())
        ):
            apps_to_install.append((app["app_url"], target["sha256"], Path(target["path"]).name))

    if not apps_to_install:
        selected_apps = "the selected scan run" if name is None else f"""'{name}'"""
        console.print(f"""[yellow]No eligible apps found to install for {selected_apps}.[/yellow]""")
        return False

    console.print(f"[bold]Installing {len(apps_to_install)} apps...[/bold]")
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(install_cli_app, *app_args) for app_args in apps_to_install]
        success_count = sum(future.result() for future in futures)

    if success_count != len(apps_to_install):
        console.print(f"[bold yellow]Installed {success_count}/{len(apps_to_install)} apps.[/bold yellow]")
        return False
    console.print(f"[bold green]Successfully installed {success_count}/{len(apps_to_install)} apps.[/bold green]")
    return True
