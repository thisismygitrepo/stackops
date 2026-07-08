import shlex
from io import StringIO

import pytest
from rich.console import Console

from stackops.jobs.installer.python_scripts import rmpc
from stackops.utils.installer_utils.linux_package_manager import LinuxDistribution


@pytest.mark.parametrize(
    ("distribution", "expected_command", "required_packages", "optional_packages"),
    [pytest.param(LinuxDistribution(distribution_id="debian"), "apt-get", rmpc.APT_REQUIRED_PACKAGES, rmpc.APT_OPTIONAL_PACKAGES, id="debian")],
)
def test_linux_companions_use_distribution_package_manager(
    monkeypatch: pytest.MonkeyPatch,
    distribution: LinuxDistribution,
    expected_command: str,
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

    assert executed_commands[0] == (("sudo", expected_command, "install", "-y", *required_packages), True)
    assert executed_commands[1:] == [(("sudo", expected_command, "install", "-y", package), False) for package in optional_packages]
    flattened_command = " ".join(part for command, _required in executed_commands for part in command)
    excluded_commands = {"apt-get", "apt", "nala", "dnf"} - {expected_command}
    assert excluded_commands.isdisjoint(flattened_command.split())


@pytest.mark.parametrize("distribution_id", ["fedora", "rhel", "centos", "rocky", "almalinux"])
def test_dnf_companions_fail_before_running_commands(monkeypatch: pytest.MonkeyPatch, distribution_id: str) -> None:
    monkeypatch.setattr(rmpc, "_run_shell", lambda *_args, **_kwargs: pytest.fail("No package command may run"))

    with pytest.raises(NotImplementedError, match="not consistently available"):
        rmpc._install_linux_companions(console=Console(file=StringIO()), distribution=LinuxDistribution(distribution_id=distribution_id))
