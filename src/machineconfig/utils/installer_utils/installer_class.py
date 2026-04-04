from machineconfig.utils.installer_utils.installer_helper import install_deb_package, download_and_prepare
from machineconfig.utils.installer_utils.install_request_logic import (
    InstallTarget,
    build_install_target,
    resolve_installer_value,
    should_skip_install,
    validate_install_request,
)
from machineconfig.jobs.installer.python_scripts.main_protocol import (
    load_installer_python_script_main,
)
from machineconfig.utils.path_extended import PathExtended
from machineconfig.utils.source_of_truth import INSTALL_VERSION_ROOT
from machineconfig.utils.installer_utils.installer_locator_utils import find_move_delete_linux, find_move_delete_windows, check_tool_exists
from machineconfig.utils.schemas.installer.installer_types import (
    InstallRequest,
    InstallationResult,
    InstallationResultFailed,
    InstallationResultSameVersion,
    InstallationResultSkipped,
    InstallationResultUpdated,
    InstallerData,
    get_normalized_arch,
    get_os_name,
)
from machineconfig.utils.installer_utils.github_release_bulk import (
    get_repo_name_from_url,
    get_release_info,
)

import platform
import subprocess


PACAKGE_MANAGERS = ["bun", "npm", "pip", "uv", "winget", "powershell", "irm", "brew", "curl", "sudo", "cargo"]


class Installer:
    def __init__(self, installer_data: InstallerData):
        self.installer_data: InstallerData = installer_data

    def __repr__(self) -> str:
        app_name = self.installer_data["appName"]
        repo_url = self.installer_data["repoURL"]
        return f"Installer of {app_name} @ {repo_url}"

    def get_description(self) -> str:
        exe_name = self._get_exe_name()
        
        old_version_cli: bool = check_tool_exists(tool_name=exe_name)
        old_version_cli_str = "✅" if old_version_cli else "❌"
        doc = self.installer_data["doc"]
        return f"{exe_name:<12} {old_version_cli_str} {doc}"
    
    def _get_exe_name(self) -> str:
        """Derive executable name from app name by converting to lowercase and removing spaces."""
        return self.installer_data["appName"].lower().replace(" ", "")  # .replace("-", "")

    def _get_installer_value(self) -> str:
        os_name = get_os_name()
        arch = get_normalized_arch()
        installer_value = self.installer_data["fileNamePattern"][arch][os_name]
        if installer_value is None:
            exe_name = self._get_exe_name()
            raise ValueError(f"No installation pattern for {exe_name} on {os_name} {arch}")
        return installer_value

    def _read_installed_version(self, exe_name: str) -> str:
        try:
            result = subprocess.run([exe_name, "--version"], capture_output=True, text=True, check=False)
        except FileNotFoundError:
            return ""
        return result.stdout.strip()

    def _resolve_install_request(self, install_request: InstallRequest) -> tuple[InstallTarget, InstallRequest]:
        installer_value = self._get_installer_value()
        install_target = build_install_target(repo_url=self.installer_data["repoURL"], installer_value=installer_value)
        install_request_resolution = validate_install_request(install_target=install_target, install_request=install_request)
        for warning in install_request_resolution.warnings:
            print(f"⚠️ WARNING: {warning}")
        return install_target, install_request_resolution.install_request

    def _build_skipped_result(self, exe_name: str) -> InstallationResultSkipped:
        return InstallationResultSkipped(
            kind="skipped",
            appName=self.installer_data["appName"],
            exeName=exe_name,
            emoji="⏭️",
            detail="already installed, skipped",
        )

    def _build_same_version_result(self, exe_name: str, version: str) -> InstallationResultSameVersion:
        return InstallationResultSameVersion(
            kind="same_version",
            appName=self.installer_data["appName"],
            exeName=exe_name,
            emoji="😑",
            version=version,
        )

    def _build_updated_result(self, exe_name: str, old_version: str, new_version: str) -> InstallationResultUpdated:
        return InstallationResultUpdated(
            kind="updated",
            appName=self.installer_data["appName"],
            exeName=exe_name,
            emoji="🤩",
            oldVersion=old_version,
            newVersion=new_version,
        )

    def _build_failed_result(self, exe_name: str, error: str) -> InstallationResultFailed:
        return InstallationResultFailed(
            kind="failed",
            appName=self.installer_data["appName"],
            exeName=exe_name,
            emoji="❌",
            error=error,
        )

    def _install_requested_with_target(self, install_target: InstallTarget, install_request: InstallRequest) -> None:
        effective_installer_value = resolve_installer_value(install_target=install_target, install_request=install_request)
        version = install_request.version if install_target.installer_kind == "github_release" or effective_installer_value.strip().startswith("winget install ") else None
        self._install_from_value(
            installer_arch_os=effective_installer_value,
            version=version,
            update=install_request.update,
        )

    def install_requested(self, install_request: InstallRequest) -> None:
        install_target, effective_install_request = self._resolve_install_request(install_request=install_request)
        self._install_requested_with_target(install_target=install_target, install_request=effective_install_request)

    def install_robust(self, install_request: InstallRequest) -> InstallationResult:
        try:
            exe_name = self._get_exe_name()
            install_target, effective_install_request = self._resolve_install_request(install_request=install_request)
            if should_skip_install(exe_name=exe_name, install_request=effective_install_request, tool_exists=check_tool_exists):
                return self._build_skipped_result(exe_name=exe_name)
            old_version_cli = self._read_installed_version(exe_name=exe_name)
            print(f"🚀 INSTALLING {exe_name.upper()} 🚀. 📊 Current version: {old_version_cli or 'Not installed'}")
            self._install_requested_with_target(install_target=install_target, install_request=effective_install_request)
            new_version_cli = self._read_installed_version(exe_name=exe_name)
            if old_version_cli == new_version_cli:
                return self._build_same_version_result(exe_name=exe_name, version=old_version_cli)
            return self._build_updated_result(exe_name=exe_name, old_version=old_version_cli, new_version=new_version_cli)
        except Exception as ex:
            exe_name = self._get_exe_name()
            print(f"❌ ERROR: Installation failed for {exe_name}: {ex}")
            return self._build_failed_result(exe_name=exe_name, error=str(ex))

    def install(self, version: str | None) -> None:
        self._install_from_value(
            installer_arch_os=self._get_installer_value(),
            version=version,
            update=False,
        )

    def _install_from_value(
        self,
        installer_arch_os: str,
        version: str | None,
        update: bool,
    ) -> None:
        exe_name = self._get_exe_name()
        repo_url = self.installer_data["repoURL"]
        version_to_be_installed: str = "unknown"  # Initialize to ensure it's always bound

        package_manager_installer = any(pm in installer_arch_os.split() for pm in PACAKGE_MANAGERS)
        script_installer = installer_arch_os.endswith((".sh", ".py", ".ps1"))
        binary_download_link = installer_arch_os.startswith("https://") or installer_arch_os.startswith("http://")

        if (repo_url == "CMD") or package_manager_installer or script_installer or binary_download_link:
            if package_manager_installer:
                from rich import print as rprint
                from rich.panel import Panel
                from rich.console import Group
                package_manager = installer_arch_os.split(" ", maxsplit=1)[0]
                print(f"📦 Using package manager: {installer_arch_os}")
                desc = package_manager + " installation"
                version_to_be_installed = version or package_manager + "Latest"
                result = subprocess.run(installer_arch_os, shell=True, capture_output=False, text=True, encoding="utf-8", check=False)
                success = result.returncode == 0
                if not success:
                    group_content = Group(f"❌ {desc} failed\nReturn code: {result.returncode}")
                    rprint(Panel(group_content, title=desc, style="red"))
                    raise RuntimeError(f"{desc} failed with return code {result.returncode}")
            elif script_installer:
                import machineconfig.jobs.installer as module
                from pathlib import Path
                search_root = Path(module.__file__).parent
                search_results = list(search_root.rglob(installer_arch_os))
                if len(search_results) == 0:
                    raise FileNotFoundError(f"Could not find installation script: {installer_arch_os}")
                elif len(search_results) > 1:
                    raise ValueError(f"Multiple installation scripts found for {installer_arch_os}: {search_results}")
                installer_path = search_results[0]
                print(f"📄 Found installation script: {installer_path}")
                if installer_arch_os.endswith(".sh"):
                    if platform.system() not in ["Linux", "Darwin"]:
                        raise NotImplementedError(f"Shell script installation not supported on {platform.system()}")
                    subprocess.run(f"bash {installer_path}", shell=True, check=True)
                    version_to_be_installed = "scripted_installation"
                elif installer_arch_os.endswith(".ps1"):
                    if platform.system() != "Windows":
                        raise NotImplementedError(f"PowerShell script installation not supported on {platform.system()}")
                    subprocess.run(f"powershell -ExecutionPolicy Bypass -File {installer_path}", shell=True, check=True)
                    version_to_be_installed = "scripted_installation"
                elif installer_arch_os.endswith(".py"):
                    import runpy
                    script_module = runpy.run_path(str(installer_path), run_name=None)
                    script_main = load_installer_python_script_main(
                        module_globals=script_module,
                        installer_path=installer_path,
                    )
                    script_main(self.installer_data, version=version, update=update)
                    version_to_be_installed = str(version)
            elif binary_download_link:
                downloaded_object = download_and_prepare(installer_arch_os)
                if downloaded_object.suffix in [".exe", ""]:  # likely an executable
                    if platform.system() == "Windows":
                        exe = find_move_delete_windows(downloaded_file_path=downloaded_object, tool_name=exe_name, delete=True, rename_to=exe_name.replace(".exe", "") + ".exe")
                    elif platform.system() in ["Linux", "Darwin"]:
                        system_name = "Linux" if platform.system() == "Linux" else "macOS"
                        print(f"🐧 Installing on {system_name}...")
                        exe = find_move_delete_linux(downloaded=downloaded_object, tool_name=exe_name, delete=True, rename_to=exe_name)
                    else:
                        error_msg = f"❌ ERROR: System {platform.system()} not supported"
                        print(error_msg)
                        raise NotImplementedError(error_msg)
                    _ = exe
                    if exe.name.replace(".exe", "") != exe_name.replace(".exe", ""):
                        from rich import print as pprint
                        from rich.panel import Panel
                        print("⚠️  Warning: Executable name mismatch")
                        pprint(Panel(f"Expected exe name: [red]{exe_name}[/red] \nAttained name: [red]{exe.name.replace('.exe', '')}[/red]", title="exe name mismatch", subtitle=repo_url))
                        new_exe_name = exe_name + ".exe" if platform.system() == "Windows" else exe_name
                        print(f"🔄 Renaming to correct name: {new_exe_name}")
                        exe.with_name(name=new_exe_name, inplace=True, overwrite=True)
                    version_to_be_installed = "downloaded_binary"
                elif downloaded_object.suffix in [".deb"]:
                    install_deb_package(downloaded_object)
                    version_to_be_installed = "downloaded_deb"
                else:
                    raise ValueError(f"Downloaded file is not an executable: {downloaded_object}")
            else:
                raise NotImplementedError(f"CMD installation method not implemented for: {installer_arch_os}")
        else:
            assert repo_url.startswith("https://github.com/"), f"repoURL must be a GitHub URL, got {repo_url}"
            downloaded, version_to_be_installed = self.binary_download(version=version)
            if str(downloaded).endswith(".deb"):
                install_deb_package(downloaded)
            else:
                if platform.system() == "Windows":
                    exe = find_move_delete_windows(downloaded_file_path=downloaded, tool_name=exe_name, delete=True, rename_to=exe_name.replace(".exe", "") + ".exe")
                elif platform.system() in ["Linux", "Darwin"]:
                    system_name = "Linux" if platform.system() == "Linux" else "macOS"
                    print(f"🐧 Installing on {system_name}...")
                    exe = find_move_delete_linux(downloaded=downloaded, tool_name=exe_name, delete=True, rename_to=exe_name)
                else:
                    error_msg = f"❌ ERROR: System {platform.system()} not supported"
                    print(error_msg)
                    raise NotImplementedError(error_msg)
                _ = exe
                if exe.name.replace(".exe", "") != exe_name.replace(".exe", ""):
                    from rich import print as pprint
                    from rich.panel import Panel
                    print("⚠️  Warning: Executable name mismatch")
                    pprint(Panel(f"Expected exe name: [red]{exe_name}[/red] \nAttained name: [red]{exe.name.replace('.exe', '')}[/red]", title="exe name mismatch", subtitle=repo_url))
                    new_exe_name = exe_name + ".exe" if platform.system() == "Windows" else exe_name
                    print(f"🔄 Renaming to correct name: {new_exe_name}")
                    exe.with_name(name=new_exe_name, inplace=True, overwrite=True)
        INSTALL_VERSION_ROOT.joinpath(exe_name).parent.mkdir(parents=True, exist_ok=True)
        INSTALL_VERSION_ROOT.joinpath(exe_name).write_text(version_to_be_installed or "unknown", encoding="utf-8")
    def binary_download(self, version: str | None) -> tuple[PathExtended, str]:
        exe_name = self._get_exe_name()
        repo_url = self.installer_data["repoURL"]
        # app_name = self.installer_data["appName"]
        download_link: str | None = None
        version_to_be_installed: str | None = None
        if "github" not in repo_url:
            # Direct download URL
            download_link = repo_url
            version_to_be_installed = "predefined_url"
            print(f"🔗 Using direct download URL: {download_link}")
            print(f"📦 Version to be installed: {version_to_be_installed}")
        else:
            # GitHub repository
            print("🌐 Retrieving release information from GitHub...")
            arch = get_normalized_arch()
            os_name = get_os_name()
            print(f"🧭 Detected system={os_name} arch={arch}")
            # Use existing get_github_release method to get download link and version
            download_link, version_to_be_installed = self.get_github_release(repo_url, version)
            # print(f"🌟 Retrieved download link from GitHub: {download_link}")
            # print(f"📦 Version to be installed: {version_to_be_installed}")
            if download_link is None:
                raise ValueError(f"Could not retrieve download link for {exe_name} version {version or 'latest'}")
            print(f"📦 Version to be installed: {version_to_be_installed}")
            print(f"🔗 Download URL: {download_link}")
        assert download_link is not None, "download_link must be set"
        assert version_to_be_installed is not None, "version_to_be_installed must be set"
        downloaded = download_and_prepare(download_link)
        return downloaded, version_to_be_installed

    def get_github_release(self, repo_url: str, version: str | None) -> tuple[str | None, str | None]:
        """
        Get download link and version from GitHub release based on fileNamePattern.
        Returns (download_url, actual_version)
        """
        arch = get_normalized_arch()
        os_name = get_os_name()
        filename_pattern = self.installer_data["fileNamePattern"][arch][os_name]
        if filename_pattern is None:
            raise ValueError(f"No fileNamePattern for {self._get_exe_name()} on {os_name} {arch}")
        repo_info = get_repo_name_from_url(repo_url)
        if not repo_info:
            print(f"❌ Invalid repository URL: {repo_url}")
            return None, None
        username, repository = repo_info
        release_info = get_release_info(username, repository, version)
        if not release_info:
            return None, None        
        actual_version = release_info.get("tag_name", "unknown") or "unknown"
        filename = filename_pattern.format(version=actual_version)

        available_filenames: list[str] = []
        for asset in release_info["assets"]:
            an_dl = asset["browser_download_url"]
            available_filenames.append(an_dl.split("/")[-1])
        if filename not in available_filenames:
            candidates = [
                filename,
                filename_pattern.format(version=actual_version),
                filename_pattern.format(version=actual_version.replace("v", "")),
            ]

            # Include hyphen/underscore variants
            variants = []
            for f in candidates:
                variants += [f, f.replace("-", "_"), f.replace("_", "-")]

            for f in variants:
                if f in available_filenames:
                    filename = f
                    break
            else:
                print(f"❌ Filename not found in assets. Tried: {variants}\nAvailable: {available_filenames}")
                return None, None
        browser_download_url = f"{repo_url}/releases/download/{actual_version}/{filename}"
        return browser_download_url, actual_version
