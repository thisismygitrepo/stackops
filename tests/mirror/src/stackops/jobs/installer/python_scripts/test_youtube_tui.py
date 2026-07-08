from collections.abc import Sequence
from io import StringIO
from typing import Literal, cast

import pytest
from rich.console import Console

from stackops.jobs.installer.python_scripts import youtube_tui
from stackops.utils.installer_utils.linux_package_manager import LinuxDistribution
from stackops.utils.schemas.installer.installer_types import InstallerData


type PackageExecutable = Literal["apt-get", "dnf", "pacman"]


@pytest.mark.parametrize(
    ("distribution", "expected_package_executable"),
    [
        pytest.param(LinuxDistribution(distribution_id="debian"), "apt-get", id="debian"),
        pytest.param(LinuxDistribution(distribution_id="fedora"), "dnf", id="fedora"),
        pytest.param(LinuxDistribution(distribution_id="arch"), "pacman", id="arch"),
    ],
)
def test_linux_dependencies_follow_distribution_instead_of_executable_precedence(
    monkeypatch: pytest.MonkeyPatch, distribution: LinuxDistribution, expected_package_executable: PackageExecutable
) -> None:
    executed_commands: list[tuple[str, ...]] = []

    def fake_run(
        command: Sequence[str] | str, console: Console, description: str, *, required: bool, env: dict[str, str] | None = None, shell: bool = False
    ) -> bool:
        _ = console, description, required, env, shell
        if isinstance(command, str):
            raise AssertionError("Linux dependency installation must use an argument sequence")
        executed_commands.append(tuple(command))
        return True

    monkeypatch.setattr(youtube_tui, "detect_current_linux_distribution", lambda: distribution)
    monkeypatch.setattr(youtube_tui.shutil, "which", lambda _name: "/usr/bin/present")
    monkeypatch.setattr(youtube_tui, "_sudo_prefix", lambda: ["sudo"])
    monkeypatch.setattr(youtube_tui, "_run", fake_run)

    youtube_tui._install_linux_dependencies(console=Console(file=StringIO()))

    package_commands = [command for command in executed_commands if len(command) > 1 and command[1] in {"apt-get", "dnf", "pacman"}]
    assert package_commands
    assert {command[1] for command in package_commands} == {expected_package_executable}
    if distribution.package_manager == "apt":
        assert package_commands[0] == ("sudo", "apt-get", "update")
        assert package_commands[1] == ("sudo", "apt-get", "install", "-y", *youtube_tui.DEBIAN_REQUIRED_PACKAGES)
    elif distribution.package_manager == "dnf":
        assert package_commands[0] == ("sudo", "dnf", "install", "-y", *youtube_tui.FEDORA_REQUIRED_PACKAGES)
    else:
        assert package_commands[0] == ("sudo", "pacman", "-S", "--needed", "--noconfirm", *youtube_tui.PACMAN_REQUIRED_PACKAGES)
    flattened_command = {part for command in executed_commands for part in command}
    excluded_commands = {"apt-get", "dnf", "pacman", "nala", "yum", "zypper", "apk"} - {expected_package_executable}
    assert excluded_commands.isdisjoint(flattened_command)


@pytest.mark.parametrize("distribution_id", ["rhel", "centos", "rocky", "almalinux"])
def test_enterprise_linux_dependencies_fail_before_running_commands(monkeypatch: pytest.MonkeyPatch, distribution_id: str) -> None:
    monkeypatch.setattr(youtube_tui, "detect_current_linux_distribution", lambda: LinuxDistribution(distribution_id=distribution_id))
    monkeypatch.setattr(youtube_tui, "_run", lambda *_args, **_kwargs: pytest.fail("No package command may run"))

    with pytest.raises(NotImplementedError, match="EPEL/CRB"):
        youtube_tui._install_linux_dependencies(console=Console(file=StringIO()))


def test_alpine_redirects_to_native_catalog_before_cargo_build(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(youtube_tui, "detect_current_linux_distribution", lambda: LinuxDistribution(distribution_id="alpine"))
    monkeypatch.setattr(youtube_tui, "_run", lambda *_args, **_kwargs: pytest.fail("No build or package command may run"))

    with pytest.raises(NotImplementedError, match=r"native installer catalog route: apk add --no-cache youtube-tui"):
        youtube_tui._install_linux_dependencies(console=Console(file=StringIO()))


def test_alpine_main_rejects_before_bootstrapping_rust(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(youtube_tui, "get_os_name", lambda: "linux")
    monkeypatch.setattr(youtube_tui, "detect_current_linux_distribution", lambda: LinuxDistribution(distribution_id="alpine"))
    monkeypatch.setattr(youtube_tui, "_ensure_rust_toolchain", lambda *_args, **_kwargs: pytest.fail("Rust bootstrap may not run"))

    with pytest.raises(NotImplementedError, match=r"apk add --no-cache youtube-tui"):
        youtube_tui.main(installer_data=cast(InstallerData, {}), version=None, update=False)
