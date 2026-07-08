import shlex

import pytest

from stackops.scripts.python.helpers.helpers_devops import cli_ssh
from stackops.utils.installer_utils.linux_package_manager import LinuxDistribution


@pytest.mark.parametrize(
    ("distribution", "expected_install_command"),
    [
        (LinuxDistribution(distribution_id="debian"), ("sudo", "apt-get", "install", "-y", "openssh-server")),
        (LinuxDistribution(distribution_id="rocky"), ("sudo", "dnf", "install", "-y", "openssh-server")),
    ],
)
def test_builds_linux_ssh_server_install_script_for_package_manager(
    distribution: LinuxDistribution, expected_install_command: tuple[str, ...]
) -> None:
    script_lines = cli_ssh._get_linux_ssh_server_install_script(distribution).splitlines()

    assert script_lines[:2] == ["#!/usr/bin/env bash", "set -euo pipefail"]
    assert tuple(shlex.split(script_lines[2])) == expected_install_command
    assert script_lines[3] == 'echo "✅ FINISHED installing openssh-server."'
