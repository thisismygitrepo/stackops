import shlex

import pytest

from stackops.jobs.installer.python_scripts import sysabc
from stackops.utils.installer_utils.linux_package_manager import LinuxDistribution


@pytest.mark.parametrize(
    ("distribution", "expected_refresh_command", "expected_install_prefix", "expected_packages"),
    [
        (
            LinuxDistribution(distribution_id="ubuntu"),
            ("sudo", "apt-get", "update"),
            ("sudo", "apt-get", "install", "-y"),
            (
                "curl",
                "wget",
                "gpg",
                "lsb-release",
                "apt-transport-https",
                "samba",
                "fuse3",
                "nfs-common",
                "git",
                "net-tools",
                "htop",
                "nano",
                "build-essential",
                "python3-dev",
                "unzip",
                "pkg-config",
                "libssl-dev",
            ),
        ),
        (
            LinuxDistribution(distribution_id="rhel"),
            ("sudo", "dnf", "makecache", "--refresh"),
            ("sudo", "dnf", "install", "-y"),
            (
                "curl",
                "wget",
                "gnupg2",
                "samba",
                "fuse3",
                "nfs-utils",
                "git",
                "net-tools",
                "nano",
                "gcc",
                "gcc-c++",
                "make",
                "python3-devel",
                "unzip",
                "pkgconf-pkg-config",
                "openssl-devel",
            ),
        ),
        (
            LinuxDistribution(distribution_id="arch"),
            ("sudo", "pacman", "-Syu", "--noconfirm"),
            ("sudo", "pacman", "-S", "--needed", "--noconfirm"),
            (
                "curl",
                "wget",
                "gnupg",
                "lsb-release",
                "samba",
                "fuse3",
                "nfs-utils",
                "git",
                "net-tools",
                "htop",
                "nano",
                "base-devel",
                "python",
                "unzip",
                "pkgconf",
                "openssl",
            ),
        ),
    ],
)
def test_builds_linux_install_script_for_package_manager(
    distribution: LinuxDistribution,
    expected_refresh_command: tuple[str, ...],
    expected_install_prefix: tuple[str, ...],
    expected_packages: tuple[str, ...],
) -> None:
    script_lines = sysabc._build_linux_install_script(distribution).splitlines()

    assert script_lines[:2] == ["#!/usr/bin/env bash", "set -euo pipefail"]
    assert tuple(shlex.split(script_lines[2])) == expected_refresh_command
    assert tuple(shlex.split(script_lines[3])) == (*expected_install_prefix, *expected_packages)
    assert script_lines[4:] == ["curl -fsSL https://bun.com/install | bash", 'sudo ln -sfn "$HOME/.bun/bin/bun" /usr/local/bin/node']
