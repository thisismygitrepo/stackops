import pytest

from stackops.jobs.installer.python_scripts import code
from stackops.utils.installer_utils.linux_package_manager import LinuxDistribution


@pytest.mark.parametrize(
    ("distribution", "expected_repository", "expected_install_command", "forbidden_tokens"),
    [
        pytest.param(
            LinuxDistribution(distribution_id="ubuntu"),
            "/etc/apt/sources.list.d/vscode.sources",
            "sudo apt-get install -y code",
            ("dnf",),
            id="apt",
        ),
        pytest.param(
            LinuxDistribution(distribution_id="rhel"),
            "/etc/yum.repos.d/vscode.repo",
            "sudo dnf install -y code",
            ("apt", "nala", "dpkg"),
            id="dnf",
        ),
    ],
)
def test_builds_official_microsoft_repository_script(
    distribution: LinuxDistribution,
    expected_repository: str,
    expected_install_command: str,
    forbidden_tokens: tuple[str, ...],
) -> None:
    script = code._build_linux_install_script(distribution)

    assert script.startswith("#!/usr/bin/env bash\nset -euo pipefail")
    assert expected_repository in script
    assert expected_install_command in script
    assert "https://packages.microsoft.com/keys/microsoft.asc" in script
    for forbidden_token in forbidden_tokens:
        assert forbidden_token not in script.lower()
