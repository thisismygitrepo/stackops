from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_network.ssh import ssh_debug_linux_utils
from stackops.utils.installer_utils.linux_package_manager import LinuxDistribution, LinuxPackageManager


@pytest.mark.parametrize(
    ("distribution", "expected_package_manager", "expected_install_command"),
    [
        pytest.param(
            LinuxDistribution(distribution_id="debian"), "apt", "sudo apt-get update && sudo apt-get install -y openssh-server", id="debian"
        ),
        pytest.param(LinuxDistribution(distribution_id="fedora"), "dnf", "sudo dnf install -y openssh-server", id="fedora"),
        pytest.param(LinuxDistribution(distribution_id="rhel"), "dnf", "sudo dnf install -y openssh-server", id="rhel"),
        pytest.param(LinuxDistribution(distribution_id="arch"), "pacman", "sudo pacman -S --needed --noconfirm openssh", id="arch"),
    ],
)
def test_detect_package_manager_follows_distribution_even_when_apt_exists(
    monkeypatch: pytest.MonkeyPatch, distribution: LinuxDistribution, expected_package_manager: LinuxPackageManager, expected_install_command: str
) -> None:
    monkeypatch.setattr(ssh_debug_linux_utils, "detect_current_linux_distribution", lambda: distribution)
    monkeypatch.setattr(Path, "exists", lambda _path: True)

    assert ssh_debug_linux_utils.detect_package_manager() == (expected_package_manager, expected_install_command)
