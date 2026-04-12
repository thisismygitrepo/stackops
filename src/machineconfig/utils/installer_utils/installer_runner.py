"""package manager"""

from pathlib import Path
from typing import cast

from machineconfig.utils.installer_utils.installer_locator_utils import check_if_installed_already
from machineconfig.utils.installer_utils.installer_class import Installer
from machineconfig.utils.installer_utils.installer_summary import render_installation_summary
from machineconfig.utils.schemas.installer.installer_types import (
    CPU_ARCHITECTURES,
    InstallRequest,
    InstallationResult,
    InstallerData,
    InstallerDataFiles,
    OPERATING_SYSTEMS,
    get_normalized_arch,
    get_os_name,
)
from machineconfig.jobs.installer.package_groups import PACKAGE_GROUP2NAMES, PACKAGE_NAME
from machineconfig.utils.path_core import delete_path
from machineconfig.utils.source_of_truth import INSTALL_VERSION_ROOT, LINUX_INSTALL_PATH, WINDOWS_INSTALL_PATH
from machineconfig.utils.files.read import read_json
from machineconfig.utils.path_reference import get_path_reference_path

from rich.console import Console
from rich.panel import Panel
import platform
import tomllib
from joblib import Parallel, delayed
import machineconfig.jobs.installer as installer_assets


def check_latest():
    console = Console()  # Added console initialization
    console.print(Panel("🔍  CHECKING FOR LATEST VERSIONS", title="Status", expand=False))  # Replaced print with Panel
    installers = get_installers(os=get_os_name(), arch=get_normalized_arch(), which_cats=["termabc"])
    installers_github: list[InstallerData] = []
    for inst__ in installers:
        app_name = inst__["appName"]
        repo_url = inst__["repoURL"]
        if "ntop" in app_name:
            print(f"⏭️  Skipping {app_name} (ntop)")
            continue
        if "github" not in repo_url:
            print(f"⏭️  Skipping {app_name} (not a GitHub release)")
            continue
        installers_github.append(inst__)

    print(f"\n🔍 Checking {len(installers_github)} GitHub-based installers...\n")

    def func(installer_data: InstallerData) -> tuple[str, str, str, str]:
        inst = Installer(installer_data=installer_data)
        exe_name = inst.installer_data["appName"].lower().replace(" ", "")
        repo_url = inst.installer_data["repoURL"]
        print(f"🔎 Checking {exe_name}...")
        _release_url, version_to_be_installed = inst.get_github_release(repo_url=repo_url, version=None)
        verdict, current_ver, new_ver = check_if_installed_already(exe_name=exe_name, version=version_to_be_installed, use_cache=False)
        return exe_name, verdict, current_ver, new_ver

    print("\n⏳ Processing installers...\n")
    res = [func(inst) for inst in installers_github]

    print("\n📊 Generating results table...\n")

    # Convert to list of dictionaries and group by status
    result_data: list[dict[str, str]] = []
    for tool, status, current_ver, new_ver in res:
        result_data.append({"Tool": tool, "Status": status, "Current Version": current_ver, "New Version": new_ver})

    # Group by status
    grouped_data: dict[str, list[dict[str, str]]] = {}
    for item in result_data:
        status = item["Status"]
        if status not in grouped_data:
            grouped_data[status] = []
        grouped_data[status].append(item)

    console.print(Panel("📊  INSTALLATION STATUS SUMMARY", title="Status", expand=False))

    # Print each group
    for status, items in grouped_data.items():
        console.print(f"\n[bold]{status.upper()}:[/bold]")
        console.rule(style="dim")
        for item in items:
            console.print(f"  {item['Tool']:<20} | Current: {item['Current Version']:<15} | New: {item['New Version']}")
    console.rule(style="dim")
    console.rule(style="bold blue")


def get_installed_cli_apps():
    print("🔍 LISTING INSTALLED CLI APPS 🔍")
    if platform.system() == "Windows":
        print("🪟 Searching for Windows executables...")
        apps = [p for p in Path(WINDOWS_INSTALL_PATH).glob("*.exe") if "notepad" not in str(p)]
    elif platform.system() in ["Linux", "Darwin"]:
        print(f"🐧 Searching for {platform.system()} executables...")
        if platform.system() == "Linux":
            apps = list(Path(LINUX_INSTALL_PATH).glob("*")) + list(Path("/usr/local/bin").glob("*"))
        else:  # Darwin/macOS
            apps = (
                list(Path(LINUX_INSTALL_PATH).glob("*"))
                + list(Path("/usr/local/bin").glob("*"))
                + list(Path("/opt/homebrew/bin").glob("*"))
            )
    else:
        error_msg = f"❌ ERROR: System {platform.system()} not supported"
        print(error_msg)
        raise NotImplementedError(error_msg)
    apps = [app for app in apps if (app.stat().st_size / 1024) > 0.1 and not app.is_symlink()]  # no symlinks like paint and wsl and bash
    print(f"✅ Found {len(apps)} installed applications")
    return apps


def get_installers(os: OPERATING_SYSTEMS, arch: CPU_ARCHITECTURES, which_cats: list[PACKAGE_NAME] | None) -> list[InstallerData]:
    res_raw: InstallerDataFiles = read_json(
        get_path_reference_path(
            module=installer_assets,
            path_reference=installer_assets.INSTALLER_DATA_PATH_REFERENCE,
        )
    )
    res_all: list[InstallerData] = res_raw["installers"]

    acceptable_apps_names: list[str] | None = None
    if which_cats is not None:
        acceptable_apps_names = []
        for cat in which_cats:
            acceptable_apps_names += PACKAGE_GROUP2NAMES[cat]
    else:
        acceptable_apps_names = None
    all_installers: list[InstallerData] = []
    for installer_data in res_all:
        if acceptable_apps_names is not None:
            if installer_data["appName"] not in acceptable_apps_names:
                continue
        try:
            if installer_data["fileNamePattern"][arch][os] is None:
                continue
        except KeyError as ke:
            print(f"❌ ERROR: Missing key in installer data: {ke}")
            print(f"Installer data: {installer_data}")
            raise KeyError(f"Missing key in installer data: {ke}")
        all_installers.append(installer_data)
    return all_installers


def _install_single_installer(installer_data: InstallerData, install_request: InstallRequest) -> InstallationResult:
    return Installer(installer_data).install_robust(install_request=install_request)


def install_bulk(
    installers_data: list[InstallerData],
    install_request: InstallRequest,
    safe: bool = False,
    jobs: int = 10,
    fresh: bool = False,
):
    print("🚀 BULK INSTALLATION PROCESS 🚀")
    if fresh:
        print("🧹 Fresh install requested - clearing version cache...")
        delete_path(Path(INSTALL_VERSION_ROOT), verbose=True)
    print("✅ Version cache cleared")
    if safe:
        pass
    print(f"🚀 Starting installation of {len(installers_data)} packages...")
    print("📦 INSTALLING FIRST PACKAGE 📦")
    first_result = Installer(installers_data[0]).install_robust(install_request=install_request)
    installers_remaining = installers_data[1:]
    print("📦 INSTALLING REMAINING PACKAGES 📦")

    delayed_jobs = [delayed(_install_single_installer)(installer, install_request) for installer in installers_remaining]
    remaining_results = cast(list[InstallationResult], list(Parallel(n_jobs=jobs)(delayed_jobs)))
    res: list[InstallationResult] = [first_result, *remaining_results]

    console = Console()
    render_installation_summary(results=res, console=console, title="📊 INSTALLATION RESULTS SUMMARY 📊")

    print("\n")
    print("✨ INSTALLATION COMPLETE ✨".center(100, "="))
    print("\n" * 2)


def get_machineconfig_version() -> str:
    from importlib.metadata import PackageNotFoundError, version as _pkg_version
    name: str = "machineconfig"
    try:
        return _pkg_version(name)
    except PackageNotFoundError:
        pass
    root: Path = Path(__file__).resolve().parents[2]
    pyproject: Path = root / "pyproject.toml"
    if pyproject.is_file():
        data: dict[str, object] = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        project = data.get("project")
        if isinstance(project, dict):
            version = project.get("version")
            if isinstance(version, str) and version:
                return version
    return "0.0.0"
