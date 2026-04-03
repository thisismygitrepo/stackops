from dataclasses import dataclass
from typing import Callable, Literal

from machineconfig.utils.schemas.installer.installer_types import InstallRequest


INSTALLER_KIND = Literal["binary_url", "cmd_raw", "github_release", "package_manager", "script"]
PACKAGE_MANAGERS: tuple[str, ...] = ("bun", "npm", "pip", "uv", "winget", "powershell", "irm", "brew", "curl", "sudo", "cargo")


@dataclass(frozen=True, slots=True)
class InstallTarget:
    installer_kind: INSTALLER_KIND
    installer_value: str


@dataclass(frozen=True, slots=True)
class InstallRequestResolution:
    install_request: InstallRequest
    warnings: tuple[str, ...]


def build_install_target(repo_url: str, installer_value: str) -> InstallTarget:
    package_manager_installer = any(package_manager in installer_value.split() for package_manager in PACKAGE_MANAGERS)
    script_installer = installer_value.endswith((".sh", ".py", ".ps1"))
    binary_download_link = installer_value.startswith("https://") or installer_value.startswith("http://")

    if package_manager_installer:
        return InstallTarget(installer_kind="package_manager", installer_value=installer_value)
    if script_installer:
        return InstallTarget(installer_kind="script", installer_value=installer_value)
    if binary_download_link:
        return InstallTarget(installer_kind="binary_url", installer_value=installer_value)
    if repo_url == "CMD":
        return InstallTarget(installer_kind="cmd_raw", installer_value=installer_value)
    return InstallTarget(installer_kind="github_release", installer_value=installer_value)


def should_skip_install(
    exe_name: str,
    install_request: InstallRequest,
    tool_exists: Callable[[str], bool],
) -> bool:
    if install_request.update or install_request.version is not None:
        return False
    return tool_exists(exe_name)


def validate_install_request(install_target: InstallTarget, install_request: InstallRequest) -> InstallRequestResolution:
    supports_update = install_target.installer_kind in {"binary_url", "github_release"} or _is_winget_install_command(install_target.installer_value)
    supports_version = install_target.installer_kind == "github_release" or _is_winget_install_command(install_target.installer_value)

    warnings: list[str] = []
    effective_update = install_request.update
    effective_version = install_request.version

    if install_request.update and not supports_update:
        warnings.append(
            f"""Unsupported --update/-u for {install_target.installer_kind} installers; update-specific handling is unavailable, so installation will continue regardless of whether the app is already installed."""
        )
    if install_request.version is not None and not supports_version:
        warnings.append(
            f"""Ignoring unsupported --version/-v for {install_target.installer_kind} installers and continuing with the supported install flow."""
        )
        effective_version = None

    return InstallRequestResolution(
        install_request=InstallRequest(version=effective_version, update=effective_update),
        warnings=tuple(warnings),
    )


def resolve_installer_value(install_target: InstallTarget, install_request: InstallRequest) -> str:
    if not _is_winget_install_command(install_target.installer_value):
        return install_target.installer_value
    if not install_request.update and install_request.version is None:
        return install_target.installer_value
    command_updated = install_target.installer_value.replace("--no-upgrade", "")
    command_updated = " ".join(command_updated.split())
    if install_request.version is not None:
        command_updated = f"{command_updated} --version {install_request.version}"
    return command_updated


def _is_winget_install_command(installer_value: str) -> bool:
    return installer_value.strip().startswith("winget install ")
