from dataclasses import dataclass
import re
from typing import Callable, Literal, assert_never

from stackops.utils.installer_utils.linux_package_manager import LINUX_PACKAGE_MANAGERS, LinuxPackageManager, detect_current_linux_distribution
from stackops.utils.schemas.installer.installer_types import (
    CPU_ARCHITECTURES,
    OPERATING_SYSTEMS,
    InstallRequest,
    InstallerData,
    LinuxPackageManagerInstallerPattern,
)


INSTALLER_KIND = Literal["binary_url", "cmd_raw", "github_release", "package_manager", "script"]
PACKAGE_MANAGERS: tuple[str, ...] = (
    "apt",
    "apt-get",
    "brew",
    "bun",
    "cargo",
    "curl",
    "dnf",
    "irm",
    "nala",
    "npm",
    "pip",
    "powershell",
    "sudo",
    "uv",
    "winget",
)
_SHELL_COMMAND_BOUNDARY = r"(?:^|[\s;&|()'\x22])"
_SHELL_EXECUTABLE_PATH = r"(?:(?:/[A-Za-z0-9_.+-]+)+/)?"
_APT_COMMAND_PATTERN = re.compile(rf"{_SHELL_COMMAND_BOUNDARY}{_SHELL_EXECUTABLE_PATH}(?:apt(?:-get)?|nala)(?=\s|$)")
_DNF_COMMAND_PATTERN = re.compile(rf"{_SHELL_COMMAND_BOUNDARY}{_SHELL_EXECUTABLE_PATH}(?:dnf|yum)(?=\s|$)")
_YUM_COMMAND_PATTERN = re.compile(rf"{_SHELL_COMMAND_BOUNDARY}{_SHELL_EXECUTABLE_PATH}yum(?=\s|$)")
_DEB_ARTIFACT_PATTERN = re.compile(r"\.deb(?:$|[^A-Za-z0-9])", flags=re.IGNORECASE)
_RPM_ARTIFACT_PATTERN = re.compile(r"\.rpm(?:$|[^A-Za-z0-9])", flags=re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class InstallTarget:
    installer_kind: INSTALLER_KIND
    installer_value: str


@dataclass(frozen=True, slots=True)
class InstallRequestResolution:
    install_request: InstallRequest
    warnings: tuple[str, ...]


def resolve_installer_pattern(installer_data: InstallerData, operating_system: OPERATING_SYSTEMS, architecture: CPU_ARCHITECTURES) -> str | None:
    architecture_patterns = installer_data["fileNamePattern"][architecture]
    match operating_system:
        case "windows":
            return architecture_patterns["windows"]
        case "darwin":
            return architecture_patterns["darwin"]
        case "linux":
            linux_pattern = architecture_patterns["linux"]
        case _:
            assert_never(operating_system)

    if linux_pattern is None:
        return None
    if isinstance(linux_pattern, str):
        incompatible_reason = _get_incompatible_linux_pattern_reason(installer_pattern=linux_pattern, package_manager=None)
        if incompatible_reason is not None:
            raise ValueError(
                f"Linux installer pattern for {installer_data['appName']} is package-manager-specific "
                f"({incompatible_reason}); declare it in the required apt/dnf mapping."
            )
        return linux_pattern

    _validate_linux_package_manager_mapping(installer_pattern=linux_pattern, app_name=installer_data["appName"])
    distribution = detect_current_linux_distribution()
    package_manager = distribution.package_manager
    match package_manager:
        case "apt":
            resolved_pattern = linux_pattern["apt"]
        case "dnf":
            resolved_pattern = linux_pattern["dnf"]
        case _:
            assert_never(package_manager)

    if resolved_pattern is None:
        return None
    incompatible_reason = _get_incompatible_linux_pattern_reason(installer_pattern=resolved_pattern, package_manager=package_manager)
    if incompatible_reason is not None:
        raise ValueError(
            f"Linux {package_manager} installer pattern for {installer_data['appName']} is incompatible "
            f"with {package_manager} ({incompatible_reason})."
        )
    return resolved_pattern


def _validate_linux_package_manager_mapping(installer_pattern: LinuxPackageManagerInstallerPattern, app_name: str) -> None:
    actual_keys = set(installer_pattern)
    required_keys = set(LINUX_PACKAGE_MANAGERS)
    if actual_keys != required_keys:
        raise ValueError(f"Linux package-manager installer pattern for {app_name} must contain exactly apt and dnf; received {sorted(actual_keys)}.")
    for package_manager, pattern in installer_pattern.items():
        if pattern is not None and not isinstance(pattern, str):
            raise TypeError(f"Linux {package_manager} installer pattern for {app_name} must be a string or null, received {type(pattern).__name__}.")
    for package_manager in LINUX_PACKAGE_MANAGERS:
        pattern = installer_pattern[package_manager]
        if pattern is None:
            continue
        incompatible_reason = _get_incompatible_linux_pattern_reason(installer_pattern=pattern, package_manager=package_manager)
        if incompatible_reason is not None:
            raise ValueError(
                f"Linux {package_manager} installer pattern for {app_name} is incompatible with {package_manager} ({incompatible_reason})."
            )


def _get_incompatible_linux_pattern_reason(installer_pattern: str, package_manager: LinuxPackageManager | None) -> str | None:
    contains_apt_command = _APT_COMMAND_PATTERN.search(installer_pattern) is not None
    contains_dnf_command = _DNF_COMMAND_PATTERN.search(installer_pattern) is not None
    contains_yum_command = _YUM_COMMAND_PATTERN.search(installer_pattern) is not None
    contains_deb_artifact = _DEB_ARTIFACT_PATTERN.search(installer_pattern) is not None
    contains_rpm_artifact = _RPM_ARTIFACT_PATTERN.search(installer_pattern) is not None

    if package_manager is None:
        if contains_apt_command or contains_dnf_command:
            return "native package-manager command"
        if contains_deb_artifact or contains_rpm_artifact:
            return "native package artifact"
        return None

    match package_manager:
        case "apt":
            if contains_dnf_command:
                return "DNF/YUM command"
            if contains_rpm_artifact:
                return "RPM artifact"
            return None
        case "dnf":
            if contains_apt_command:
                return "APT/Nala command"
            if contains_yum_command:
                return "legacy YUM command"
            if contains_deb_artifact:
                return "DEB artifact"
            return None
        case _:
            assert_never(package_manager)


def build_install_target(repo_url: str, installer_value: str) -> InstallTarget:
    package_manager_installer = is_package_manager_command(installer_value)
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


def is_package_manager_command(installer_value: str) -> bool:
    contains_native_linux_manager = (
        _APT_COMMAND_PATTERN.search(installer_value) is not None or _DNF_COMMAND_PATTERN.search(installer_value) is not None
    )
    contains_other_manager = any(package_manager in installer_value.split() for package_manager in PACKAGE_MANAGERS)
    return contains_native_linux_manager or contains_other_manager


def should_skip_install(exe_name: str, install_request: InstallRequest, tool_exists: Callable[[str], bool]) -> bool:
    if install_request.update or install_request.version is not None:
        return False
    return tool_exists(exe_name)


def validate_install_request(install_target: InstallTarget, install_request: InstallRequest) -> InstallRequestResolution:
    supports_update = (
        install_target.installer_kind in {"binary_url", "github_release", "script"}
        or _is_winget_install_command(install_target.installer_value)
        or _is_uv_tool_install_command(install_target.installer_value)
    )
    supports_version = install_target.installer_kind in {"github_release", "script"} or _is_winget_install_command(install_target.installer_value)

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

    return InstallRequestResolution(install_request=InstallRequest(version=effective_version, update=effective_update), warnings=tuple(warnings))


def resolve_installer_value(install_target: InstallTarget, install_request: InstallRequest) -> str:
    if _is_uv_tool_install_command(install_target.installer_value) and install_request.update:
        return _add_uv_upgrade(install_target.installer_value)
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


def _is_uv_tool_install_command(installer_value: str) -> bool:
    return installer_value.strip().startswith("uv tool install ")


def _add_uv_upgrade(installer_value: str) -> str:
    parts = installer_value.strip().split()
    if "--upgrade" in parts:
        return installer_value
    return f"{installer_value.strip()} --upgrade"
