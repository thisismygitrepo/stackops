from stackops.utils.schemas.installer.package_groups import PACKAGE_GROUP2NAMES
from stackops.utils.path_core import delete_path
from stackops.utils.schemas.installer.installer_types import InstallerData
from pathlib import Path
from stackops.utils.files.compression import DECOMPRESS_SUPPORTED_FORMATS, decompress_path
from stackops.utils.installer_utils.linux_package_file import is_linux_package_file
from stackops.utils.source_of_truth import INSTALL_TMP_DIR


def _is_supported_archive(path: Path) -> bool:
    return not is_linux_package_file(path) and str(path).endswith(DECOMPRESS_SUPPORTED_FORMATS)


def get_group_name_to_repr() -> dict[str, str]:
    # Build category options and maintain a mapping from display text to actual category name
    category_display_to_name: dict[str, str] = {}
    for group_name, group_values in PACKAGE_GROUP2NAMES.items():
        display = f"📦 {group_name:<20}" + "   --   " + f"{'|'.join(group_values):<60}"
        category_display_to_name[display] = group_name
    return category_display_to_name


def handle_installer_not_found(search_term: str, app_apps: list[InstallerData]) -> list[str]:
    """Handle installer not found with friendly suggestions using fuzzy matching."""
    from difflib import get_close_matches

    all_names = sorted([inst["appName"] for inst in app_apps])
    name_to_doc = {inst["appName"]: inst["doc"] for inst in app_apps}
    all_descriptions = {f"{inst['appName']}: {inst['doc']}": inst["appName"] for inst in app_apps}

    close_name_matches = get_close_matches(search_term, all_names, n=5, cutoff=0.4)
    close_description_matches = get_close_matches(search_term, list(all_descriptions.keys()), n=5, cutoff=0.4)

    search_lower = search_term.lower()
    substring_matches = [inst["appName"] for inst in app_apps if search_lower in inst["appName"].lower() or search_lower in inst["doc"].lower()]

    ordered_matches: list[str] = list(
        dict.fromkeys(close_name_matches + [all_descriptions[desc] for desc in close_description_matches] + substring_matches)
    )

    order_matches_with_docs = [f"{app_name:<20} : " + name_to_doc.get(app_name, "") for app_name in ordered_matches]
    from stackops.utils.options_utils.options import choose_from_options

    chosen = choose_from_options(
        options=order_matches_with_docs, msg=f"🔍 No installer found for '[red]{search_term}[/red]'. Did you mean one of these?", multi=True, tv=True
    )
    if chosen is None or len(chosen) == 0:
        print("\n❌ Selection cancelled by user.")
        return []
    apps_chosen = [app.split(" : ")[0].strip() for app in chosen]
    print(f"➡️  You selected: {apps_chosen}")
    return apps_chosen
    # top_matches = ordered_matches[:10] if len(ordered_matches) > 10 else ordered_matches
    # from rich.console import Console
    # from rich.panel import Panel
    # from rich.table import Table
    # console = Console()
    # console.print(f"\n❌ '[red]{search_term}[/red]' was not found.", style="bold")
    # if top_matches:
    #     console.print("🤔 Did you mean one of these?", style="yellow")
    #     table = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    #     table.add_column("#", justify="right", width=3)
    #     table.add_column("Installer", style="green")
    #     table.add_column("Description", style="dim", overflow="fold")
    #     for i, match in enumerate(top_matches, 1):
    #         table.add_row(f"[cyan]{i}[/cyan]", match, name_to_doc.get(match, ""))
    #     console.print(table)
    # else:
    #     console.print("📋 Here are some available options:", style="blue")
    #     # Show first 10 installers as examples
    #     if len(all_names) > 10:
    #         sample_names = all_names[:10]
    #     else:
    #         sample_names = all_names
    #     table = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    #     table.add_column("#", justify="right", width=3)
    #     table.add_column("Installer", style="green")
    #     table.add_column("Description", style="dim", overflow="fold")
    #     for i, name in enumerate(sample_names, 1):
    #         table.add_row(f"[cyan]{i}[/cyan]", name, name_to_doc.get(name, ""))
    #     console.print(table)
    #     if len(all_names) > 10:
    #         console.print(f"   [dim]... and {len(all_names) - 10} more[/dim]")

    # panel = Panel(f"[bold blue]💡 Use 'ia' to interactively browse all available installers.[/bold blue]\n[bold blue]💡 Use one of the categories: {list(PACKAGE_GROUP2NAMES.keys())}[/bold blue]", title="[yellow]Helpful Tips[/yellow]", border_style="yellow")
    # console.print(panel)


def install_msi_package(downloaded: Path) -> None:
    from rich import print as rprint
    from rich.console import Group
    from rich.panel import Panel
    import platform
    import subprocess

    assert platform.system() == "Windows"
    print(f"📦 Installing .msi package: {downloaded}")
    result = subprocess.run(["msiexec.exe", "/i", str(downloaded), "/qn", "/norestart"], capture_output=True, text=True, check=False)
    if result.returncode not in {0, 3010}:
        sub_panels = []
        if result.stdout:
            sub_panels.append(Panel(result.stdout, title="STDOUT", style="blue"))
        if result.stderr:
            sub_panels.append(Panel(result.stderr, title="STDERR", style="red"))
        group_content = Group(f"❌ Installing .msi failed\nReturn code: {result.returncode}", *sub_panels)
        rprint(Panel(group_content, title="Installing .msi", style="red"))
        raise RuntimeError(f"Installing .msi failed with return code {result.returncode}")
    print("🗑️  Cleaning up .msi package...")
    downloaded.unlink(missing_ok=True)


def install_dmg_package(downloaded: Path) -> None:
    import platform
    import subprocess
    import tempfile

    if platform.system() != "Darwin":
        raise RuntimeError("DMG packages can only be installed on macOS.")
    with tempfile.TemporaryDirectory(prefix="stackops-dmg-") as mount_directory:
        mount_point = Path(mount_directory)
        subprocess.run(
            ["/usr/bin/hdiutil", "attach", "-nobrowse", "-readonly", "-mountpoint", str(mount_point), str(downloaded)],
            capture_output=True,
            text=True,
            check=True,
        )
        try:
            applications = [
                candidate
                for candidate in mount_point.iterdir()
                if candidate.is_dir() and not candidate.is_symlink() and candidate.suffix.lower() == ".app"
            ]
            if len(applications) != 1:
                raise FileNotFoundError(f"Expected one application bundle in {mount_point}, found {len(applications)}.")
            applications_root = Path("/Applications")
            with tempfile.TemporaryDirectory(prefix=".stackops-install-", dir=applications_root) as staging_directory:
                staging_root = Path(staging_directory)
                staged_application = staging_root.joinpath(applications[0].name)
                subprocess.run(["/usr/bin/ditto", str(applications[0]), str(staged_application)], check=True)
                if not staged_application.is_dir():
                    raise FileNotFoundError(f"DMG application staging failed: {staged_application}.")

                destination = applications_root.joinpath(applications[0].name)
                previous_application = staging_root.joinpath(f"{applications[0].name}.previous")
                had_previous_application = destination.exists() or destination.is_symlink()
                if had_previous_application:
                    destination.rename(previous_application)
                try:
                    staged_application.rename(destination)
                except OSError:
                    if had_previous_application:
                        previous_application.rename(destination)
                    raise
        finally:
            subprocess.run(["/usr/bin/hdiutil", "detach", str(mount_point)], capture_output=True, text=True, check=True)
    downloaded.unlink(missing_ok=True)


def download_and_prepare(download_url: str) -> Path:
    from stackops.utils.files.download import download

    downloaded_object = download(download_url, output_dir=str(INSTALL_TMP_DIR))
    if downloaded_object is None:
        raise ValueError(f"Failed to download from URL: {download_url}")
    archive_path = Path(downloaded_object).expanduser()
    extracted_path = archive_path
    if extracted_path.is_file() and _is_supported_archive(archive_path):
        extracted_path = decompress_path(archive_path, folder=None, name=None, path=None, inplace=False, orig=False, verbose=True)
        delete_path(archive_path, verbose=True)
        if extracted_path.is_dir():
            nested_items = list(extracted_path.glob("*"))
            if len(nested_items) == 1:
                nested_path = nested_items[0]
                if nested_path.is_file() and _is_supported_archive(nested_path):
                    extracted_path = decompress_path(nested_path, folder=None, name=None, path=None, inplace=False, orig=False, verbose=True)
                    delete_path(nested_path, verbose=True)
    elif extracted_path.is_dir() and len([p for p in extracted_path.rglob("*") if not p.name.startswith(".")]) == 1:
        only_file_in = next(extracted_path.glob("*"))
        if only_file_in.is_file() and _is_supported_archive(only_file_in):
            extracted_path = decompress_path(only_file_in, folder=None, name=None, path=None, inplace=False, orig=False, verbose=True)
            delete_path(only_file_in, verbose=True)
    return extracted_path
