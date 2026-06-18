from dataclasses import dataclass
from collections.abc import Mapping
import platform
import shlex
from typing import Callable, Literal

from stackops.utils.schemas.installer.installer_types import InstallRequest


INSTALLER_KIND = Literal["binary_url", "cmd_raw", "github_release", "package_manager", "script"]
PACKAGE_MANAGERS: tuple[str, ...] = ("bun", "npm", "pip", "uv", "winget", "powershell", "irm", "brew", "curl", "sudo", "cargo")
APT_FAMILY_PACKAGE_MANAGERS: frozenset[str] = frozenset({"apt", "apt-get", "nala"})
APT_FAMILY_LINUX_IDS: frozenset[str] = frozenset(
    {
        "debian",
        "ubuntu",
        "linuxmint",
        "pop",
        "elementary",
        "zorin",
        "neon",
        "raspbian",
        "kali",
        "parrot",
        "mx",
        "devuan",
        "deepin",
        "peppermint",
        "tuxedo",
    }
)


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

    return InstallRequestResolution(
        install_request=InstallRequest(version=effective_version, update=effective_update),
        warnings=tuple(warnings),
    )


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


def get_unsupported_apt_family_command_reason(installer_value: str) -> str | None:
    if not _starts_with_sudo_apt_family_command(installer_value):
        return None
    if is_apt_family_linux():
        return None
    command_display = _first_shell_command_display(installer_value)
    return (
        f"apt/nala installer skipped: `{command_display}` is only supported on Debian/Ubuntu-style Linux; "
        f"detected {_describe_current_os()}."
    )


def is_apt_family_linux(os_release: Mapping[str, str] | None = None) -> bool:
    if os_release is None:
        if platform.system() != "Linux":
            return False
        release_info = _read_linux_os_release()
    else:
        release_info = os_release
    release_ids = _linux_os_release_ids(release_info)
    return len(release_ids & APT_FAMILY_LINUX_IDS) > 0


def _starts_with_sudo_apt_family_command(installer_value: str) -> bool:
    try:
        command_parts = shlex.split(_first_shell_command_display(installer_value))
    except ValueError:
        command_parts = installer_value.strip().split()
    return len(command_parts) >= 2 and command_parts[0] == "sudo" and command_parts[1] in APT_FAMILY_PACKAGE_MANAGERS


def _first_shell_command_display(installer_value: str) -> str:
    return installer_value.strip().split(";", maxsplit=1)[0].strip()


def _read_linux_os_release() -> Mapping[str, str]:
    try:
        return platform.freedesktop_os_release()
    except OSError:
        return {}


def _linux_os_release_ids(os_release: Mapping[str, str]) -> frozenset[str]:
    release_ids: set[str] = set()
    for key in ("ID", "ID_LIKE"):
        raw_value = os_release.get(key, "")
        for token in raw_value.replace(",", " ").split():
            normalized_token = token.strip().lower()
            if normalized_token != "":
                release_ids.add(normalized_token)
    return frozenset(release_ids)


def _describe_current_os() -> str:
    system_name = platform.system()
    if system_name != "Linux":
        return system_name
    release_info = _read_linux_os_release()
    release_ids = _linux_os_release_ids(release_info)
    if len(release_ids) == 0:
        return "unknown Linux distribution"
    return "Linux distribution " + "/".join(sorted(release_ids))
