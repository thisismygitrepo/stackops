import pytest

from stackops.jobs.installer.python_scripts import redis
from stackops.utils.installer_utils.linux_package_manager import LinuxDistribution


@pytest.mark.parametrize(
    ("distribution", "expected_repository", "expected_install_command", "expected_service", "forbidden_tokens"),
    [
        pytest.param(
            LinuxDistribution(distribution_id="debian"),
            "https://packages.redis.io/deb",
            "sudo apt-get install -y redis",
            "sudo systemctl enable --now redis-server",
            ("dnf",),
            id="apt",
        ),
        pytest.param(
            LinuxDistribution(distribution_id="rhel"),
            None,
            "sudo dnf install -y redis",
            "sudo systemctl enable --now redis",
            ("apt", "nala", "dpkg"),
            id="dnf",
        ),
        pytest.param(
            LinuxDistribution(distribution_id="arch"),
            None,
            "sudo pacman -S --needed --noconfirm valkey",
            "sudo systemctl enable --now redis",
            ("apt", "nala", "dpkg", "dnf", "yum"),
            id="pacman",
        ),
    ],
)
def test_builds_native_redis_script(
    distribution: LinuxDistribution,
    expected_repository: str | None,
    expected_install_command: str,
    expected_service: str,
    forbidden_tokens: tuple[str, ...],
) -> None:
    script = redis._build_linux_install_script(distribution)

    assert script.startswith("#!/usr/bin/env bash\nset -euo pipefail")
    assert expected_install_command in script
    assert expected_service in script
    assert "redis-cli ping" in script
    if expected_repository is not None:
        assert expected_repository in script
    for forbidden_token in forbidden_tokens:
        assert forbidden_token not in script.lower()
