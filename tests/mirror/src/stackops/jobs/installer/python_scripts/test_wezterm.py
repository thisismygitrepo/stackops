import pytest

from stackops.jobs.installer.python_scripts import wezterm
from stackops.utils.installer_utils.linux_package_manager import LinuxDistribution


@pytest.mark.parametrize(
    ("distribution", "expected_repository_command", "expected_install_command", "forbidden_tokens"),
    [
        pytest.param(
            LinuxDistribution(distribution_id="ubuntu"),
            "https://apt.fury.io/wez/",
            "sudo apt-get install -y wezterm",
            ("dnf",),
            id="apt",
        ),
        pytest.param(
            LinuxDistribution(distribution_id="rhel"),
            "sudo dnf copr enable -y wezfurlong/wezterm-nightly",
            "sudo dnf install -y wezterm",
            ("apt", "nala", "dpkg"),
            id="dnf",
        ),
    ],
)
def test_builds_official_wezterm_repository_script(
    distribution: LinuxDistribution,
    expected_repository_command: str,
    expected_install_command: str,
    forbidden_tokens: tuple[str, ...],
) -> None:
    script = wezterm._build_linux_install_script(distribution)

    assert script.startswith("#!/usr/bin/env bash\nset -euo pipefail")
    assert expected_repository_command in script
    assert expected_install_command in script
    for forbidden_token in forbidden_tokens:
        assert forbidden_token not in script.lower()
