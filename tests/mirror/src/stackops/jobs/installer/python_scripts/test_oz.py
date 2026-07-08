import pytest

from stackops.jobs.installer.python_scripts import oz
from stackops.utils.installer_utils.linux_package_manager import LinuxDistribution


@pytest.mark.parametrize(
    ("distribution", "expected_tokens", "forbidden_tokens"),
    [
        (LinuxDistribution(distribution_id="debian"), ("apt-get", "/etc/apt/keyrings", "oz-stable"), ("dnf", "/etc/yum.repos.d")),
        (LinuxDistribution(distribution_id="rhel"), ("dnf", "/etc/yum.repos.d", "oz-stable"), ("apt-get", "/etc/apt")),
        (
            LinuxDistribution(distribution_id="arch"),
            ("pacman -Syu --noconfirm", "/etc/pacman.conf", "pacman-key", "oz-stable"),
            ("apt-get", "dnf", "/etc/apt", "/etc/yum.repos.d"),
        ),
    ],
)
def test_builds_native_oz_repository_script(
    distribution: LinuxDistribution, expected_tokens: tuple[str, ...], forbidden_tokens: tuple[str, ...]
) -> None:
    program = oz._build_linux_install_script(distribution=distribution)

    assert all(token in program for token in expected_tokens)
    assert all(token not in program for token in forbidden_tokens)
