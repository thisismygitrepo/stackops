from pathlib import Path

from rich.console import Console

from stackops.utils.installer_utils.installer_runner import get_installed_cli_apps
from stackops.utils.source_of_truth import INSTALL_VERSION_ROOT

console = Console()


def collect_apps_to_scan(app_names: list[str] | None) -> list[tuple[Path, str | None]]:
    with console.status("[bold green]Gathering installed applications...[/bold green]"):
        apps_paths = get_installed_cli_apps()
        if app_names is not None:
            normalized = {name.strip().lower() for name in app_names if name.strip()}
            apps_paths = [app_path for app_path in apps_paths if app_path.stem.lower() in normalized]
        versions: dict[str, str] = {}
        for version_file in Path(INSTALL_VERSION_ROOT).glob("*"):
            if version_file.is_file() and not version_file.name.startswith("."):
                versions[version_file.stem] = version_file.read_text(encoding="utf-8").strip()
        apps_to_scan = [(app_path, versions.get(app_path.stem)) for app_path in apps_paths]
    return apps_to_scan
