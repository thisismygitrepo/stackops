from pathlib import Path
from typing import cast

import pytest

from stackops.utils.installer_utils import install_request_logic, installer_runner
from stackops.utils.installer_utils.linux_package_manager import LinuxDistribution, LinuxDistributionId
from stackops.utils.schemas.installer.installer_types import CPU_ARCHITECTURES, InstallerData, InstallerDataFiles, LinuxInstallerPattern


def _build_installer_data(app_name: str, linux_pattern: LinuxInstallerPattern) -> InstallerData:
    return cast(
        InstallerData,
        {
            "appName": app_name,
            "license": "MIT",
            "doc": "test installer",
            "repoURL": "CMD",
            "categoryLabels": ["system-setup"],
            "fileNamePattern": {
                "amd64": {"windows": None, "linux": linux_pattern, "darwin": None},
                "arm64": {"windows": None, "linux": linux_pattern, "darwin": None},
            },
        },
    )


def test_get_installers_skips_null_pattern_for_current_package_manager(monkeypatch: pytest.MonkeyPatch) -> None:
    portable_installer = _build_installer_data(app_name="Portable Tool", linux_pattern="portable-tool-linux.tar.gz")
    apt_only_installer = _build_installer_data(app_name="APT-only Tool", linux_pattern={"apt": "sudo apt-get install -y apt-only-tool", "dnf": None})
    installer_file = InstallerDataFiles(version="1", installers=[portable_installer, apt_only_installer])
    monkeypatch.setattr(installer_runner, "read_json", lambda _path: installer_file)
    monkeypatch.setattr(installer_runner, "get_path_reference_path", lambda *, module, path_reference: Path(path_reference))
    monkeypatch.setattr(install_request_logic, "detect_current_linux_distribution", lambda: LinuxDistribution(distribution_id="rhel"))

    installers = installer_runner.get_installers(os="linux", arch="amd64", which_cats=None)

    assert installers == [portable_installer]


@pytest.mark.parametrize("distribution_id", ["ubuntu", "rhel"])
@pytest.mark.parametrize("architecture", ["amd64", "arm64"])
def test_installer_catalog_resolves_for_supported_package_managers(
    monkeypatch: pytest.MonkeyPatch, distribution_id: LinuxDistributionId, architecture: CPU_ARCHITECTURES
) -> None:
    monkeypatch.setattr(install_request_logic, "detect_current_linux_distribution", lambda: LinuxDistribution(distribution_id=distribution_id))

    installers = installer_runner.get_installers(os="linux", arch=architecture, which_cats=None)

    assert len(installers) > 0
