import pytest

from stackops.utils.cli_utils import command_lookup
from stackops.utils.installer_utils import install_request_logic, installer_cli, installer_runner
from stackops.utils.installer_utils.installer_class import Installer
from stackops.utils.installer_utils.linux_package_manager import LinuxDistribution, LinuxDistributionId
from stackops.utils.schemas.installer.installer_types import CPU_ARCHITECTURES, OPERATING_SYSTEMS, InstallerData
from stackops.utils.schemas.installer.package_groups import PACKAGE_NAME


def test_install_if_missing_skips_unavailable_platform_installer_without_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    def tool_is_missing(_tool_name: str) -> bool:
        return False

    def no_installers(os: OPERATING_SYSTEMS, arch: CPU_ARCHITECTURES, which_cats: list[PACKAGE_NAME] | None) -> list[InstallerData]:
        _ = os, arch, which_cats
        return []

    def fail_if_general_cli_is_called(**_kwargs: object) -> None:
        raise AssertionError("Dependency installation must not enter the general interactive CLI")

    monkeypatch.setattr(command_lookup, "check_tool_exists", tool_is_missing)
    monkeypatch.setattr(installer_runner, "get_installers", no_installers)
    monkeypatch.setattr(installer_cli, "main_installer_cli", fail_if_general_cli_is_called)

    installed = installer_cli.install_if_missing(which="7zip", binary_name="7z", verbose=False)

    assert not installed


@pytest.mark.parametrize("architecture", ("amd64", "arm64"))
def test_7zip_is_available_on_dnf_linux(architecture: CPU_ARCHITECTURES, monkeypatch: pytest.MonkeyPatch) -> None:
    def detect_fedora() -> LinuxDistribution:
        return LinuxDistribution(distribution_id="fedora")

    monkeypatch.setattr(install_request_logic, "detect_current_linux_distribution", detect_fedora)

    installers = installer_runner.get_installers(os="linux", arch=architecture, which_cats=None)
    seven_zip = next(installer for installer in installers if installer["appName"] == "7zip")
    installer_value = install_request_logic.resolve_installer_pattern(installer_data=seven_zip, operating_system="linux", architecture=architecture)

    assert installer_value == "sudo dnf install -y 7zip"
    assert Installer(installer_data=seven_zip).get_exe_name() == "7z"


@pytest.mark.parametrize(
    ("architecture", "distribution_id", "expected_pattern"),
    (
        ("amd64", "ubuntu", "orca-ide_{version}_amd64.deb"),
        ("arm64", "ubuntu", "orca-ide_{version}_arm64.deb"),
        ("amd64", "fedora", "orca-ide-{version}.x86_64.rpm"),
        ("arm64", "fedora", "orca-ide-{version}.aarch64.rpm"),
    ),
)
def test_orca_linux_packages_install_the_gui_and_cli(
    architecture: CPU_ARCHITECTURES, distribution_id: LinuxDistributionId, expected_pattern: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    def detect_distribution() -> LinuxDistribution:
        return LinuxDistribution(distribution_id=distribution_id)

    def detect_linux() -> str:
        return "Linux"

    monkeypatch.setattr(install_request_logic, "detect_current_linux_distribution", detect_distribution)
    monkeypatch.setattr("stackops.utils.installer_utils.installer_class.platform.system", detect_linux)

    installers = installer_runner.get_installers(os="linux", arch=architecture, which_cats=None)
    orca = next(installer for installer in installers if installer["appName"] == "orca")
    installer_value = install_request_logic.resolve_installer_pattern(installer_data=orca, operating_system="linux", architecture=architecture)

    assert installer_value == expected_pattern
    assert Installer(installer_data=orca).get_exe_name() == "orca-ide"
