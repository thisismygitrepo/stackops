from io import StringIO
from typing import cast

import pytest
from rich.console import Console

from stackops.jobs.installer.python_scripts import termusic
from stackops.utils.installer_utils.linux_package_manager import LinuxDistribution
from stackops.utils.schemas.installer.installer_types import InstallerData


@pytest.mark.parametrize(
    ("distribution", "expected_install_prefix", "required_package_groups", "optional_packages"),
    [
        pytest.param(
            LinuxDistribution(distribution_id="debian"),
            ("apt-get", "install", "-y"),
            termusic.APT_REQUIRED_PACKAGE_GROUPS,
            termusic.APT_OPTIONAL_PACKAGES,
            id="debian",
        ),
        pytest.param(
            LinuxDistribution(distribution_id="fedora"),
            ("dnf", "install", "-y"),
            termusic.DNF_REQUIRED_PACKAGE_GROUPS,
            termusic.DNF_OPTIONAL_PACKAGES,
            id="fedora",
        ),
        pytest.param(
            LinuxDistribution(distribution_id="arch"),
            ("pacman", "-S", "--needed", "--noconfirm"),
            termusic.PACMAN_REQUIRED_PACKAGE_GROUPS,
            termusic.PACMAN_OPTIONAL_PACKAGES,
            id="arch",
        ),
    ],
)
def test_linux_dependencies_use_distribution_package_manager(
    monkeypatch: pytest.MonkeyPatch,
    distribution: LinuxDistribution,
    expected_install_prefix: tuple[str, ...],
    required_package_groups: tuple[tuple[str, ...], ...],
    optional_packages: tuple[str, ...],
) -> None:
    executed_commands: list[tuple[str, ...]] = []

    def fake_run_command(command: list[str], console: Console, description: str, *, required: bool) -> bool:
        _ = console, description, required
        executed_commands.append(tuple(command))
        return True

    monkeypatch.setattr(termusic.platform, "freedesktop_os_release", lambda: {"ID": distribution.distribution_id})
    monkeypatch.setattr(termusic, "detect_current_linux_distribution", lambda: distribution)
    monkeypatch.setattr(termusic, "_sudo_prefix", lambda: ["sudo"])
    monkeypatch.setattr(termusic, "_run_command", fake_run_command)

    termusic._install_linux_dependencies(console=Console(file=StringIO()))

    expected_packages = tuple(group[0] for group in required_package_groups) + optional_packages
    assert executed_commands == [("sudo", *expected_install_prefix, package) for package in expected_packages]
    flattened_command = " ".join(part for command in executed_commands for part in command)
    excluded_commands = {"apt-get", "apt", "nala", "dnf", "pacman"} - {expected_install_prefix[0]}
    assert excluded_commands.isdisjoint(flattened_command.split())


@pytest.mark.parametrize("distribution_id", ["rhel", "centos", "rocky", "almalinux"])
def test_enterprise_linux_dependencies_fail_before_running_commands(monkeypatch: pytest.MonkeyPatch, distribution_id: str) -> None:
    monkeypatch.setattr(termusic, "detect_current_linux_distribution", lambda: LinuxDistribution(distribution_id=distribution_id))
    monkeypatch.setattr(termusic, "_run_command", lambda *_args, **_kwargs: pytest.fail("No package command may run"))

    with pytest.raises(NotImplementedError, match="EPEL/CRB"):
        termusic._install_linux_dependencies(console=Console(file=StringIO()))


def test_alpine_dependencies_fail_before_downloading_glibc_release(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(termusic, "detect_current_linux_distribution", lambda: LinuxDistribution(distribution_id="alpine"))
    monkeypatch.setattr(termusic, "_run_command", lambda *_args, **_kwargs: pytest.fail("No package command may run"))

    with pytest.raises(NotImplementedError, match="musl-linked Alpine Linux"):
        termusic._install_linux_dependencies(console=Console(file=StringIO()))


def test_alpine_main_rejects_before_downloading_release_archive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(termusic, "get_os_name", lambda: "linux")
    monkeypatch.setattr(termusic, "detect_current_linux_distribution", lambda: LinuxDistribution(distribution_id="alpine"))
    monkeypatch.setattr(termusic, "_install_termusic_binaries", lambda *_args, **_kwargs: pytest.fail("Release download may not run"))

    with pytest.raises(NotImplementedError, match="musl-linked Alpine Linux"):
        termusic.main(installer_data=cast(InstallerData, {}), version=None, update=False)
