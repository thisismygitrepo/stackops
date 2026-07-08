import shlex
from io import StringIO
from typing import cast

import pytest
from rich.console import Console

from stackops.jobs.installer.python_scripts import rmpc
from stackops.utils.installer_utils.linux_package_manager import LinuxDistribution
from stackops.utils.schemas.installer.installer_types import InstallerData


@pytest.mark.parametrize(
    ("distribution", "expected_install_prefix", "required_packages", "optional_packages"),
    [
        pytest.param(
            LinuxDistribution(distribution_id="debian"),
            ("apt-get", "install", "-y"),
            rmpc.APT_REQUIRED_PACKAGES,
            rmpc.APT_OPTIONAL_PACKAGES,
            id="debian",
        ),
        pytest.param(
            LinuxDistribution(distribution_id="arch"),
            ("pacman", "-S", "--needed", "--noconfirm"),
            rmpc.PACMAN_REQUIRED_PACKAGES,
            rmpc.PACMAN_OPTIONAL_PACKAGES,
            id="arch",
        ),
    ],
)
def test_linux_companions_use_distribution_package_manager(
    monkeypatch: pytest.MonkeyPatch,
    distribution: LinuxDistribution,
    expected_install_prefix: tuple[str, ...],
    required_packages: tuple[str, ...],
    optional_packages: tuple[str, ...],
) -> None:
    executed_commands: list[tuple[tuple[str, ...], bool]] = []

    def fake_run_shell(command: str, console: Console, description: str, *, required: bool) -> bool:
        _ = console, description
        executed_commands.append((tuple(shlex.split(command)), required))
        return True

    monkeypatch.setattr(rmpc, "_sudo", lambda: "sudo ")
    monkeypatch.setattr(rmpc, "_run_shell", fake_run_shell)

    rmpc._install_linux_companions(console=Console(file=StringIO()), distribution=distribution)

    assert executed_commands[0] == (("sudo", *expected_install_prefix, *required_packages), True)
    assert executed_commands[1:] == [(("sudo", *expected_install_prefix, package), False) for package in optional_packages]
    flattened_command = " ".join(part for command, _required in executed_commands for part in command)
    excluded_commands = {"apt-get", "apt", "nala", "dnf", "pacman"} - {expected_install_prefix[0]}
    assert excluded_commands.isdisjoint(flattened_command.split())


@pytest.mark.parametrize("distribution_id", ["fedora", "rhel", "centos", "rocky", "almalinux"])
def test_dnf_companions_fail_before_running_commands(monkeypatch: pytest.MonkeyPatch, distribution_id: str) -> None:
    monkeypatch.setattr(rmpc, "_run_shell", lambda *_args, **_kwargs: pytest.fail("No package command may run"))

    with pytest.raises(NotImplementedError, match="not consistently available"):
        rmpc._install_linux_companions(console=Console(file=StringIO()), distribution=LinuxDistribution(distribution_id=distribution_id))


def test_alpine_companions_redirect_to_native_catalog_before_running_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rmpc, "_run_shell", lambda *_args, **_kwargs: pytest.fail("No package command may run"))

    with pytest.raises(NotImplementedError, match=r"native installer catalog route: apk add --no-cache rmpc"):
        rmpc._install_linux_companions(console=Console(file=StringIO()), distribution=LinuxDistribution(distribution_id="alpine"))


def test_alpine_main_rejects_before_downloading_release_archive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rmpc, "get_os_name", lambda: "linux")
    monkeypatch.setattr(rmpc.platform, "system", lambda: "Linux")
    monkeypatch.setattr(rmpc, "detect_current_linux_distribution", lambda: LinuxDistribution(distribution_id="alpine"))
    monkeypatch.setattr(rmpc, "Installer", lambda *_args, **_kwargs: pytest.fail("Release installer may not run"))

    with pytest.raises(NotImplementedError, match=r"apk add --no-cache rmpc"):
        rmpc.main(installer_data=cast(InstallerData, {}), version=None, update=False)
