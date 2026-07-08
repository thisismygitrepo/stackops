import pytest

from stackops.jobs.installer.python_scripts import brave
from stackops.utils.installer_utils.linux_package_manager import LinuxDistribution


def test_apt_script_uses_brave_sources_file() -> None:
    distribution = LinuxDistribution(distribution_id="ubuntu")

    script = brave._build_linux_install_script(distribution)

    assert script.startswith("#!/usr/bin/env bash\nset -euo pipefail")
    assert "https://brave-browser-apt-release.s3.brave.com/brave-browser.sources" in script
    assert "sudo apt-get install -y brave-browser" in script
    assert "dnf" not in script.lower()
    assert "nala" not in script.lower()


def test_fedora_script_uses_dnf5_repository_syntax() -> None:
    distribution = LinuxDistribution(distribution_id="fedora")

    script = brave._build_linux_install_script(distribution)

    assert "sudo dnf config-manager addrepo --from-repofile=https://brave-browser-rpm-release.s3.brave.com/brave-browser.repo" in script
    assert "sudo dnf install -y brave-browser" in script
    for apt_only_token in ("apt", "nala", "dpkg"):
        assert apt_only_token not in script.lower()


@pytest.mark.parametrize("distribution_id", ["rhel", "rocky", "centos"])
def test_enterprise_linux_script_uses_dnf4_repository_syntax(distribution_id: str) -> None:
    distribution = LinuxDistribution(distribution_id=distribution_id)

    script = brave._build_linux_install_script(distribution)

    assert "sudo dnf config-manager --add-repo https://brave-browser-rpm-release.s3.brave.com/brave-browser.repo" in script
    assert "sudo dnf install -y brave-browser" in script
    for apt_only_token in ("apt", "nala", "dpkg"):
        assert apt_only_token not in script.lower()


def test_rejects_rpm_distribution_without_official_brave_instructions() -> None:
    distribution = LinuxDistribution(distribution_id="almalinux")

    with pytest.raises(NotImplementedError, match="almalinux"):
        brave._build_linux_install_script(distribution)
