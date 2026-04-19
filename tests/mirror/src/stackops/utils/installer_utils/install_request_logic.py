

from stackops.utils.installer_utils.install_request_logic import (
    InstallTarget,
    build_install_target,
    resolve_installer_value,
    should_skip_install,
    validate_install_request,
)
from stackops.utils.schemas.installer.installer_types import InstallRequest


def test_build_install_target_classifies_installer_value() -> None:
    assert build_install_target("https://github.com/owner/repo", "uv tool install").installer_kind == "package_manager"
    assert build_install_target("https://github.com/owner/repo", "setup.sh").installer_kind == "script"
    assert build_install_target("https://github.com/owner/repo", "https://downloads.example/tool").installer_kind == "binary_url"
    assert build_install_target("CMD", "echo hi").installer_kind == "cmd_raw"
    assert build_install_target("https://github.com/owner/repo", "tool-{version}.tar.gz").installer_kind == "github_release"


def test_should_skip_install_only_when_existing_binary_can_be_reused() -> None:
    install_request = InstallRequest(version=None, update=False)

    assert should_skip_install("tool", install_request, lambda tool_name: tool_name == "tool")
    assert not should_skip_install("tool", InstallRequest(version="v1.0.0", update=False), lambda tool_name: True)
    assert not should_skip_install("tool", InstallRequest(version=None, update=True), lambda tool_name: True)


def test_validate_install_request_preserves_only_supported_flags() -> None:
    install_target = InstallTarget(installer_kind="script", installer_value="setup.sh")

    resolution = validate_install_request(install_target=install_target, install_request=InstallRequest(version="v2.0.0", update=True))

    assert resolution.install_request == InstallRequest(version=None, update=True)
    assert len(resolution.warnings) == 2
    assert "Unsupported --update/-u" in resolution.warnings[0]
    assert "Ignoring unsupported --version/-v" in resolution.warnings[1]


def test_resolve_installer_value_updates_winget_command() -> None:
    install_target = InstallTarget(installer_kind="package_manager", installer_value="winget install example.tool --no-upgrade")

    resolved = resolve_installer_value(install_target=install_target, install_request=InstallRequest(version="1.2.3", update=True))

    assert resolved == "winget install example.tool --version 1.2.3"
